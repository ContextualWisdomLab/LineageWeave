-- ADR 0362: product UI copy is a versioned LineageWeave read-model resource.
-- Ontology/concept labels remain outside this schema and with their canonical owner.
begin;

alter table user_account
    drop constraint if exists user_account_preferred_locale_ck;

alter table user_account
    add constraint user_account_preferred_locale_ck
    check (
        preferred_locale is null
        or preferred_locale in ('ko', 'en', 'ja', 'zh', 'vi', 'es', 'de', 'fr')
    );

create table if not exists ui_translation_resource (
    resource_id bigint generated always as identity primary key,
    product_key text not null check (
        product_key <> ''
        and btrim(
            product_key,
            chr(9) || chr(10) || chr(11) || chr(12) || chr(13)
            || chr(28) || chr(29) || chr(30) || chr(31) || chr(32)
            || chr(133) || chr(160) || chr(5760)
            || chr(8192) || chr(8193) || chr(8194) || chr(8195) || chr(8196)
            || chr(8197) || chr(8198) || chr(8199) || chr(8200) || chr(8201) || chr(8202)
            || chr(8232) || chr(8233) || chr(8239) || chr(8287) || chr(12288)
        ) = product_key
        and position(':' in product_key) = 0
    ),
    screen_key text not null check (
        screen_key <> ''
        and btrim(
            screen_key,
            chr(9) || chr(10) || chr(11) || chr(12) || chr(13)
            || chr(28) || chr(29) || chr(30) || chr(31) || chr(32)
            || chr(133) || chr(160) || chr(5760)
            || chr(8192) || chr(8193) || chr(8194) || chr(8195) || chr(8196)
            || chr(8197) || chr(8198) || chr(8199) || chr(8200) || chr(8201) || chr(8202)
            || chr(8232) || chr(8233) || chr(8239) || chr(8287) || chr(12288)
        ) = screen_key
        and position(':' in screen_key) = 0
    ),
    resource_version bigint not null check (resource_version > 0),
    publication_state text not null default 'draft' check (publication_state in ('draft', 'published')),
    created_at timestamptz not null default now(),
    published_at timestamptz,
    unique (product_key, screen_key, resource_version),
    check (
        (publication_state = 'draft' and published_at is null)
        or (publication_state = 'published' and published_at is not null)
    )
);

create table if not exists ui_translation_key (
    resource_id bigint not null references ui_translation_resource(resource_id) on delete cascade,
    translation_key text not null check (
        translation_key <> ''
        and btrim(
            translation_key,
            chr(9) || chr(10) || chr(11) || chr(12) || chr(13)
            || chr(28) || chr(29) || chr(30) || chr(31) || chr(32)
            || chr(133) || chr(160) || chr(5760)
            || chr(8192) || chr(8193) || chr(8194) || chr(8195) || chr(8196)
            || chr(8197) || chr(8198) || chr(8199) || chr(8200) || chr(8201) || chr(8202)
            || chr(8232) || chr(8233) || chr(8239) || chr(8287) || chr(12288)
        ) = translation_key
    ),
    primary key (resource_id, translation_key)
);

create table if not exists ui_translation_text (
    translation_text_id bigint generated always as identity primary key,
    resource_id bigint not null,
    translation_key text not null,
    locale text not null check (locale in ('ko', 'en', 'ja', 'zh', 'vi', 'es', 'de', 'fr')),
    translated_text text not null check (
        btrim(
            translated_text,
            chr(9) || chr(10) || chr(11) || chr(12) || chr(13)
            || chr(28) || chr(29) || chr(30) || chr(31) || chr(32)
            || chr(133) || chr(160) || chr(5760)
            || chr(8192) || chr(8193) || chr(8194) || chr(8195) || chr(8196)
            || chr(8197) || chr(8198) || chr(8199) || chr(8200) || chr(8201) || chr(8202)
            || chr(8232) || chr(8233) || chr(8239) || chr(8287) || chr(12288)
        ) <> ''
    ),
    unique (resource_id, translation_key, locale),
    foreign key (resource_id, translation_key)
        references ui_translation_key(resource_id, translation_key)
        on delete cascade
);

create index if not exists ui_translation_resource_latest_published_idx
    on ui_translation_resource(product_key, screen_key, resource_version desc)
    where publication_state = 'published';

create or replace function guard_ui_translation_resource_mutation()
returns trigger
language plpgsql
as $$
begin
    if tg_op = 'INSERT' then
        if new.publication_state <> 'draft' then
            raise exception 'UI translation resources must be created as draft';
        end if;
        return new;
    end if;

    if old.publication_state = 'published' then
        raise exception 'published UI translation resource % is immutable', old.resource_id;
    end if;

    if tg_op = 'DELETE' then
        return old;
    end if;

    if old.product_key is distinct from new.product_key
       or old.screen_key is distinct from new.screen_key
       or old.resource_version is distinct from new.resource_version then
        raise exception 'UI translation resource % identity is immutable after creation', old.resource_id;
    end if;

    if new.publication_state = 'published' then
        if not exists (
            select 1
              from ui_translation_key
             where resource_id = old.resource_id
        ) then
            raise exception 'UI translation resource % has no screen keys', old.resource_id;
        end if;

        if exists (
            select 1
              from ui_translation_key as required_key
              cross join (
                  values ('ko'), ('en'), ('ja'), ('zh'), ('vi'), ('es'), ('de'), ('fr')
              ) as required_locale(locale)
              left join ui_translation_text as translated
                on translated.resource_id = required_key.resource_id
               and translated.translation_key = required_key.translation_key
               and translated.locale = required_locale.locale
             where required_key.resource_id = old.resource_id
               and translated.translation_text_id is null
        ) then
            raise exception 'UI translation resource % is incomplete for the eight-locale contract', old.resource_id;
        end if;
        new.published_at := statement_timestamp();
    end if;

    return new;
end;
$$;

create or replace function guard_ui_translation_child_mutation()
returns trigger
language plpgsql
as $$
declare
    target_resource_id bigint;
    target_state text;
begin
    if tg_op = 'UPDATE' and old.resource_id <> new.resource_id then
        raise exception 'UI translation child rows cannot move between resources';
    end if;

    if tg_op = 'DELETE' then
        target_resource_id := old.resource_id;
    else
        target_resource_id := new.resource_id;
    end if;

    select publication_state
      into target_state
      from ui_translation_resource
     where resource_id = target_resource_id
     for update;

    if target_state = 'published' then
        raise exception 'published UI translation resource % is immutable', target_resource_id;
    end if;

    if tg_op = 'DELETE' then
        return old;
    end if;
    return new;
end;
$$;

drop trigger if exists ui_translation_resource_mutation_guard on ui_translation_resource;
create trigger ui_translation_resource_mutation_guard
before insert or update or delete on ui_translation_resource
for each row execute function guard_ui_translation_resource_mutation();

drop trigger if exists ui_translation_key_mutation_guard on ui_translation_key;
create trigger ui_translation_key_mutation_guard
before insert or update or delete on ui_translation_key
for each row execute function guard_ui_translation_child_mutation();

drop trigger if exists ui_translation_text_mutation_guard on ui_translation_text;
create trigger ui_translation_text_mutation_guard
before insert or update or delete on ui_translation_text
for each row execute function guard_ui_translation_child_mutation();

commit;
