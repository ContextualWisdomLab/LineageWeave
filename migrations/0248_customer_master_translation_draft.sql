-- Customer Master v1 copy candidate for ADR 0362.
-- This migration seeds a complete eight-locale DRAFT only. Publication remains
-- a separate, review-gated action so unreviewed copy cannot become immutable.
begin;

create temporary table customer_master_translation_seed (
    translation_key text primary key,
    ko text not null,
    en text not null,
    ja text not null,
    zh text not null,
    vi text not null,
    es text not null,
    de text not null,
    fr text not null
) on commit drop;

insert into customer_master_translation_seed(
    translation_key, ko, en, ja, zh, vi, es, de, fr
)
values
    ('A counterparty can hold more than one role over time -- a customer in one post can be a competitor, supplier, or partner in another. Every role observed for a name is listed, not just the most frequent.', '하나의 거래 상대방은 시간에 따라 여러 역할을 가질 수 있습니다. 한 게시물의 고객이 다른 게시물에서는 경쟁사, 공급업체 또는 파트너일 수 있습니다. 이름별로 가장 빈번한 역할만이 아니라 관측된 모든 역할을 표시합니다.', 'A counterparty can hold more than one role over time -- a customer in one post can be a competitor, supplier, or partner in another. Every role observed for a name is listed, not just the most frequent.', '取引先は時間の経過とともに複数の役割を持つことがあります。ある投稿では顧客でも、別の投稿では競合、仕入先、またはパートナーである場合があります。名前ごとに、最も多い役割だけでなく観測されたすべての役割を表示します。', '同一交易对手可随时间承担多个角色：在一条帖子中是客户，在另一条帖子中也可能是竞争对手、供应商或合作伙伴。系统会列出某个名称下已观察到的所有角色，而不只是最常见的角色。', 'Một đối tác có thể đảm nhiệm nhiều vai trò theo thời gian -- là khách hàng trong một bài đăng nhưng có thể là đối thủ, nhà cung cấp hoặc đối tác trong bài đăng khác. Hệ thống liệt kê mọi vai trò đã quan sát theo từng tên, không chỉ vai trò xuất hiện nhiều nhất.', 'Una contraparte puede desempeñar más de un rol a lo largo del tiempo: puede ser cliente en una publicación y competidor, proveedor o socio en otra. Se muestran todos los roles observados para cada nombre, no solo el más frecuente.', 'Eine Gegenpartei kann im Zeitverlauf mehrere Rollen haben: In einem Beitrag kann sie Kunde sein, in einem anderen Wettbewerber, Lieferant oder Partner. Für jeden Namen werden alle beobachteten Rollen aufgeführt, nicht nur die häufigste.', 'Une contrepartie peut avoir plusieurs rôles au fil du temps : elle peut être cliente dans une publication, puis concurrente, fournisseur ou partenaire dans une autre. Tous les rôles observés pour un nom sont affichés, et pas seulement le plus fréquent.'),
    ('Affiliates of {name}', '{name}의 계열사', 'Affiliates of {name}', '{name} の関連会社', '{name} 的关联公司', 'Các đơn vị liên kết của {name}', 'Empresas afiliadas de {name}', 'Verbundene Unternehmen von {name}', 'Entités affiliées à {name}'),
    ('Author context', '작성자 맥락', 'Author context', '作成者コンテキスト', '作者上下文', 'Ngữ cảnh tác giả', 'Contexto del autor', 'Autorenkontext', 'Contexte de l’auteur'),
    ('Authorization context', '권한 맥락', 'Authorization context', '認可コンテキスト', '授权上下文', 'Ngữ cảnh phân quyền', 'Contexto de autorización', 'Autorisierungskontext', 'Contexte d’autorisation'),
    ('Authorized customer scope', '권한이 있는 고객 범위', 'Authorized customer scope', '認可された顧客範囲', '已授权的客户范围', 'Phạm vi khách hàng được cấp quyền', 'Ámbito de clientes autorizado', 'Autorisierter Kundenumfang', 'Périmètre client autorisé'),
    ('Customer entities available to this account.', '이 계정에서 볼 수 있는 고객 엔터티입니다.', 'Customer entities available to this account.', 'このアカウントで利用できる顧客エンティティです。', '此账户可访问的客户实体。', 'Các thực thể khách hàng mà tài khoản này được phép truy cập.', 'Entidades de clientes disponibles para esta cuenta.', 'Für dieses Konto verfügbare Kundenentitäten.', 'Entités clientes accessibles à ce compte.'),
    ('Customer master could not be loaded.', '고객 마스터를 불러오지 못했습니다.', 'Customer master could not be loaded.', '顧客マスターを読み込めませんでした。', '无法加载客户主数据。', 'Không thể tải dữ liệu chủ khách hàng.', 'No se pudo cargar el maestro de clientes.', 'Die Kundenstammdaten konnten nicht geladen werden.', 'Impossible de charger le référentiel clients.'),
    ('Customer master', '고객 마스터', 'Customer master', '顧客マスター', '客户主数据', 'Dữ liệu chủ khách hàng', 'Maestro de clientes', 'Kundenstammdaten', 'Référentiel clients'),
    ('Hint only', '힌트만', 'Hint only', 'ヒントのみ', '仅作提示', 'Chỉ là gợi ý', 'Solo como indicio', 'Nur als Hinweis', 'Indication uniquement'),
    ('Keymen', '핵심 인물', 'Keymen', 'キーパーソン', '关键人物', 'Nhân sự chủ chốt', 'Personas clave', 'Schlüsselpersonen', 'Personnes clés'),
    ('Loading customer master...', '고객 마스터를 불러오는 중...', 'Loading customer master...', '顧客マスターを読み込んでいます...', '正在加载客户主数据...', 'Đang tải dữ liệu chủ khách hàng...', 'Cargando el maestro de clientes...', 'Kundenstammdaten werden geladen...', 'Chargement du référentiel clients...'),
    ('Loading related posts...', '관련 게시물을 불러오는 중...', 'Loading related posts...', '関連投稿を読み込んでいます...', '正在加载相关帖子...', 'Đang tải các bài đăng liên quan...', 'Cargando publicaciones relacionadas...', 'Zugehörige Beiträge werden geladen...', 'Chargement des publications associées...'),
    ('Multiple roles observed', '여러 역할이 관측됨', 'Multiple roles observed', '複数の役割を観測', '观察到多个角色', 'Đã quan sát nhiều vai trò', 'Se observaron varios roles', 'Mehrere Rollen beobachtet', 'Plusieurs rôles observés'),
    ('No customer entities are connected to this account.', '이 계정에 연결된 고객 엔터티가 없습니다.', 'No customer entities are connected to this account.', 'このアカウントに接続された顧客エンティティはありません。', '此账户没有关联的客户实体。', 'Không có thực thể khách hàng nào được liên kết với tài khoản này.', 'No hay entidades de clientes conectadas a esta cuenta.', 'Mit diesem Konto sind keine Kundenentitäten verbunden.', 'Aucune entité cliente n’est associée à ce compte.'),
    ('No linked posts yet.', '연결된 게시물이 아직 없습니다.', 'No linked posts yet.', '関連投稿はまだありません。', '暂无关联帖子。', 'Chưa có bài đăng liên kết.', 'Aún no hay publicaciones vinculadas.', 'Noch keine verknüpften Beiträge.', 'Aucune publication associée pour le moment.'),
    ('No post body.', '게시물 본문이 없습니다.', 'No post body.', '投稿本文がありません。', '无帖子正文。', 'Không có nội dung bài đăng.', 'No hay contenido de la publicación.', 'Kein Beitragsinhalt.', 'Aucun contenu de publication.'),
    ('Observed customer evidence', '관측된 고객 근거', 'Observed customer evidence', '観測された顧客エビデンス', '已观察的客户证据', 'Bằng chứng khách hàng đã quan sát', 'Evidencia de clientes observada', 'Beobachtete Kundenevidenz', 'Éléments de preuve client observés'),
    ('Open record', '기록 열기', 'Open record', 'レコードを開く', '打开记录', 'Mở bản ghi', 'Abrir registro', 'Datensatz öffnen', 'Ouvrir l’enregistrement'),
    ('Open related post: {label}', '관련 게시물 열기: {label}', 'Open related post: {label}', '関連投稿を開く: {label}', '打开相关帖子：{label}', 'Mở bài đăng liên quan: {label}', 'Abrir publicación relacionada: {label}', 'Zugehörigen Beitrag öffnen: {label}', 'Ouvrir la publication associée : {label}'),
    ('Our-side Keymen hints', '당사 측 핵심 인물 힌트', 'Our-side Keymen hints', '自社側キーパーソンのヒント', '我方关键人物提示', 'Gợi ý nhân sự chủ chốt phía chúng ta', 'Indicios sobre personas clave de nuestra organización', 'Hinweise auf Schlüsselpersonen auf unserer Seite', 'Indications sur les personnes clés de notre côté'),
    ('Post body preview', '게시물 본문 미리보기', 'Post body preview', '投稿本文のプレビュー', '帖子正文预览', 'Xem trước nội dung bài đăng', 'Vista previa del contenido de la publicación', 'Vorschau des Beitragsinhalts', 'Aperçu du contenu de la publication'),
    ('Related posts', '관련 게시물', 'Related posts', '関連投稿', '相关帖子', 'Các bài đăng liên quan', 'Publicaciones relacionadas', 'Zugehörige Beiträge', 'Publications associées'),
    ('Relationship network', '관계 네트워크', 'Relationship network', '関係ネットワーク', '关系网络', 'Mạng lưới quan hệ', 'Red de relaciones', 'Beziehungsnetzwerk', 'Réseau de relations'),
    ('Resolve', '확정', 'Resolve', '解決', '解析', 'Xác minh', 'Resolver', 'Auflösen', 'Résoudre'),
    ('Resolving...', '확정 중...', 'Resolving...', '解決中...', '正在解析...', 'Đang xác minh...', 'Resolviendo...', 'Wird aufgelöst...', 'Résolution en cours...'),
    ('Retry', '다시 시도', 'Retry', '再試行', '重试', 'Thử lại', 'Reintentar', 'Erneut versuchen', 'Réessayer'),
    ('Retry needed', '다시 시도 필요', 'Retry needed', '再試行が必要です', '需要重试', 'Cần thử lại', 'Es necesario reintentar', 'Erneuter Versuch erforderlich', 'Nouvel essai requis'),
    ('Shown as top level: listed parent forms a cycle.', '상위 수준에 표시됨: 지정된 상위 항목이 순환 관계를 만듭니다.', 'Shown as top level: listed parent forms a cycle.', '最上位として表示: 指定された親が循環を形成します。', '显示为顶层：所列父项会形成循环。', 'Hiển thị ở cấp cao nhất: mục cha được chỉ định tạo thành một chu trình.', 'Se muestra en el nivel superior: el elemento padre indicado forma un ciclo.', 'Als oberste Ebene angezeigt: Das angegebene übergeordnete Element bildet einen Zyklus.', 'Affiché au niveau supérieur : le parent indiqué forme un cycle.'),
    ('Shown as top level: entity lists itself as parent.', '상위 수준에 표시됨: 엔터티가 자기 자신을 상위 항목으로 지정했습니다.', 'Shown as top level: entity lists itself as parent.', '最上位として表示: エンティティが自身を親として指定しています。', '显示为顶层：该实体将自身列为父项。', 'Hiển thị ở cấp cao nhất: thực thể tự chỉ định chính nó làm mục cha.', 'Se muestra en el nivel superior: la entidad se indica a sí misma como elemento padre.', 'Als oberste Ebene angezeigt: Die Entität gibt sich selbst als übergeordnetes Element an.', 'Affiché au niveau supérieur : l’entité se désigne elle-même comme parent.'),
    ('Shown as top level: listed parent is not visible.', '상위 수준에 표시됨: 지정된 상위 항목을 볼 수 없습니다.', 'Shown as top level: listed parent is not visible.', '最上位として表示: 指定された親は表示対象ではありません。', '显示为顶层：所列父项当前不可见。', 'Hiển thị ở cấp cao nhất: mục cha được chỉ định không hiển thị.', 'Se muestra en el nivel superior: el elemento padre indicado no está visible.', 'Als oberste Ebene angezeigt: Das angegebene übergeordnete Element ist nicht sichtbar.', 'Affiché au niveau supérieur : le parent indiqué n’est pas visible.'),
    ('This request failed. Retry the same action.', '요청이 실패했습니다. 같은 작업을 다시 시도하세요.', 'This request failed. Retry the same action.', 'リクエストに失敗しました。同じ操作をもう一度お試しください。', '请求失败。请重试同一操作。', 'Yêu cầu không thành công. Hãy thử lại cùng thao tác.', 'La solicitud falló. Vuelva a intentar la misma acción.', 'Diese Anfrage ist fehlgeschlagen. Wiederholen Sie dieselbe Aktion.', 'La requête a échoué. Réessayez la même action.'),
    ('Showing the first {shown} of {total} observed customer identifiers, ranked by post count.', '게시물 수 기준으로 순위를 매긴 관측 고객 식별자 {total}개 중 처음 {shown}개를 표시합니다.', 'Showing the first {shown} of {total} observed customer identifiers, ranked by post count.', '投稿数で順位付けした観測済み顧客識別子 {total} 件のうち、先頭 {shown} 件を表示しています。', '按帖子数排序后，显示已观察客户标识符共 {total} 个中的前 {shown} 个。', 'Hiển thị {shown} mã định danh khách hàng đầu tiên trong tổng số {total} mã đã quan sát, xếp hạng theo số bài đăng.', 'Se muestran los primeros {shown} de {total} identificadores de clientes observados, ordenados por número de publicaciones.', 'Die ersten {shown} von {total} beobachteten Kundenkennungen werden angezeigt, nach Anzahl der Beiträge sortiert.', 'Affichage des {shown} premiers identifiants client observés sur {total}, classés par nombre de publications.'),
    ('Showing the first {shown} of {total} observed source authors, ranked by post count.', '게시물 수 기준으로 순위를 매긴 관측 원천 작성자 {total}명 중 처음 {shown}명을 표시합니다.', 'Showing the first {shown} of {total} observed source authors, ranked by post count.', '投稿数で順位付けした観測済みソース作成者 {total} 名のうち、先頭 {shown} 名を表示しています。', '按帖子数排序后，显示已观察来源作者共 {total} 名中的前 {shown} 名。', 'Hiển thị {shown} tác giả nguồn đầu tiên trong tổng số {total} tác giả đã quan sát, xếp hạng theo số bài đăng.', 'Se muestran los primeros {shown} de {total} autores de origen observados, ordenados por número de publicaciones.', 'Die ersten {shown} von {total} beobachteten Quellautoren werden angezeigt, nach Anzahl der Beiträge sortiert.', 'Affichage des {shown} premiers auteurs source observés sur {total}, classés par nombre de publications.'),
    ('Source identifiers are hints only; ontology and semantic evidence must resolve them before binding a customer.', '원천 식별자는 힌트일 뿐입니다. 고객과 연결하기 전에 온톨로지와 의미 근거로 확인해야 합니다.', 'Source identifiers are hints only; ontology and semantic evidence must resolve them before binding a customer.', 'ソース識別子はヒントにすぎません。顧客に紐付ける前に、オントロジーとセマンティックエビデンスで解決する必要があります。', '来源标识符仅作为提示；在绑定客户之前，必须通过本体和语义证据进行解析确认。', 'Mã định danh nguồn chỉ là gợi ý; bằng chứng ontology và ngữ nghĩa phải xác minh chúng trước khi liên kết với khách hàng.', 'Los identificadores de origen son solo indicios; la ontología y la evidencia semántica deben resolverlos antes de vincular un cliente.', 'Quellkennungen sind nur Hinweise; Ontologie und semantische Evidenz müssen sie auflösen, bevor ein Kunde zugeordnet wird.', 'Les identifiants source ne sont que des indications ; l’ontologie et les éléments de preuve sémantiques doivent les résoudre avant toute association à un client.'),
    ('This hint could not be resolved to a corroborated organization name.', '이 힌트를 뒷받침되는 조직명으로 확인하지 못했습니다.', 'This hint could not be resolved to a corroborated organization name.', 'このヒントを裏付けのある組織名として解決できませんでした。', '无法将此提示解析为有佐证的组织名称。', 'Không thể xác minh gợi ý này thành tên tổ chức có bằng chứng xác nhận.', 'No se pudo resolver este indicio como un nombre de organización corroborado.', 'Dieser Hinweis konnte keinem belegten Organisationsnamen zugeordnet werden.', 'Cette indication n’a pas pu être résolue en un nom d’organisation corroboré.'),
    ('Unresolved source identifier', '해결되지 않은 원천 식별자', 'Unresolved source identifier', '未解決のソース識別子', '未解析的来源标识符', 'Mã định danh nguồn chưa được giải quyết', 'Identificador de origen sin resolver', 'Nicht aufgelöste Quellkennung', 'Identifiant source non résolu'),
    ('posts', '게시물', 'posts', '投稿', '帖子', 'bài đăng', 'publicaciones', 'Beiträge', 'publications');

do $customer_master_seed$
declare
    target_resource_id bigint;
    target_state text;
    expected_key_count integer;
begin
    select count(*) into expected_key_count
      from customer_master_translation_seed;

    if expected_key_count <> 37 then
        raise exception 'Customer Master translation seed expected 37 keys, found %',
            expected_key_count;
    end if;

    select resource_id, publication_state
      into target_resource_id, target_state
      from ui_translation_resource
     where product_key = 'lineageweave'
       and screen_key = 'customer-master'
       and resource_version = 1;

    if target_resource_id is null then
        insert into ui_translation_resource(
            product_key, screen_key, resource_version
        )
        values ('lineageweave', 'customer-master', 1)
        on conflict (product_key, screen_key, resource_version) do nothing
        returning resource_id, publication_state
             into target_resource_id, target_state;

        if target_resource_id is null then
            -- A concurrent 0248 replay may have won the root insert while this
            -- transaction waited on the ownership reservation. Adopt only the
            -- resource that the same migration bound as owned; an external
            -- collision remains fail-closed.
            select resource_id, publication_state
              into target_resource_id, target_state
              from ui_translation_resource
             where product_key = 'lineageweave'
               and screen_key = 'customer-master'
               and resource_version = 1
             for update;

            if target_resource_id is null
               or not exists (
                   select 1
                     from ui_translation_seed_ownership
                    where migration_key = '0248_customer_master_translation_draft'
                      and ownership_state = 'owned'
                      and resource_id = target_resource_id
               ) then
                raise exception
                    'Customer Master seed root insert collided with an unowned resource';
            end if;
        end if;
    end if;

    if exists (
        select 1
          from ui_translation_key as actual
          left join customer_master_translation_seed as expected
            on expected.translation_key = actual.translation_key
         where actual.resource_id = target_resource_id
           and expected.translation_key is null
    ) then
        raise exception
            'Customer Master translation draft contains keys outside the reviewed seed';
    end if;

    if target_state = 'published' then
        if (
            select count(*)
              from ui_translation_key
             where resource_id = target_resource_id
        ) <> expected_key_count
        or (
            select count(*)
              from ui_translation_text
             where resource_id = target_resource_id
        ) <> expected_key_count * 8
        or exists (
            select 1
              from customer_master_translation_seed as expected
              cross join lateral (
                  values
                      ('ko', expected.ko),
                      ('en', expected.en),
                      ('ja', expected.ja),
                      ('zh', expected.zh),
                      ('vi', expected.vi),
                      ('es', expected.es),
                      ('de', expected.de),
                      ('fr', expected.fr)
              ) as localized(locale, translated_text)
              left join ui_translation_text as actual
                on actual.resource_id = target_resource_id
               and actual.translation_key = expected.translation_key
               and actual.locale = localized.locale
             where actual.translation_text is distinct from localized.translated_text
        ) then
            raise exception
                'Published Customer Master translation v1 differs from the migration seed';
        end if;
        return;
    end if;

    insert into ui_translation_key(resource_id, translation_key)
    select target_resource_id, translation_key
      from customer_master_translation_seed
    on conflict (resource_id, translation_key) do nothing;

    insert into ui_translation_text(
        resource_id, translation_key, locale, translated_text
    )
    select
        target_resource_id,
        expected.translation_key,
        localized.locale,
        localized.translated_text
      from customer_master_translation_seed as expected
      cross join lateral (
          values
              ('ko', expected.ko),
              ('en', expected.en),
              ('ja', expected.ja),
              ('zh', expected.zh),
              ('vi', expected.vi),
              ('es', expected.es),
              ('de', expected.de),
              ('fr', expected.fr)
      ) as localized(locale, translated_text)
    on conflict (resource_id, translation_key, locale)
    do update set translated_text = excluded.translated_text;

    if (
        select count(*)
          from ui_translation_key
         where resource_id = target_resource_id
    ) <> expected_key_count
    or (
        select count(*)
          from ui_translation_text
         where resource_id = target_resource_id
    ) <> expected_key_count * 8 then
        raise exception
            'Customer Master translation draft failed the eight-locale completeness check';
    end if;

    -- Deliberately remain draft. A later reviewed publication action performs
    -- the one-way transition and receives the database-owned published_at.
end;
$customer_master_seed$;

commit;