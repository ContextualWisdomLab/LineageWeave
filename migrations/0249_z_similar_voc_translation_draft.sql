-- Similar VOC v1 buyer-copy candidate for ADR 0362.
-- This is reviewable draft data only; publication remains a separate one-way
-- action after language/product review and unchanged-head consumer acceptance.
begin;

select set_config(
    'lineageweave.migration_file',
    '0249_z_similar_voc_translation_draft.sql',
    true
);

create temporary table similar_voc_translation_seed (
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

insert into similar_voc_translation_seed(
    translation_key, ko, en, ja, zh, vi, es, de, fr
)
values
    ('Similar VOC · customer cohort', '유사 VOC · 고객군 확인', 'Similar VOC · customer cohort', '類似VOC・顧客群', '相似VOC · 客户群', 'VOC tương tự · nhóm khách hàng', 'VOC similares · cohorte de clientes', 'Ähnliche VOC · Kundengruppe', 'VOC similaires · cohorte client'),
    ('Review prior evidence and action history adjudicated as the same issue type.', '같은 문제 유형으로 판정된 과거 근거와 조치 이력을 확인하세요.', 'Review prior evidence and action history adjudicated as the same issue type.', '同じ問題タイプと判定された過去の根拠と対応履歴を確認します。', '查看被判定为同一问题类型的历史证据和处置记录。', 'Xem bằng chứng trước đây và lịch sử xử lý được xác định là cùng loại vấn đề.', 'Revise la evidencia anterior y el historial de acciones clasificados como el mismo tipo de problema.', 'Prüfen Sie frühere Nachweise und Maßnahmen, die demselben Problemtyp zugeordnet wurden.', 'Consultez les éléments de preuve antérieurs et l’historique des actions classés dans le même type de problème.'),
    ('The retained evidence remains visible. Retry the failed next page.', '불러온 근거는 그대로 유지됩니다. 실패한 다음 페이지를 다시 요청하세요.', 'The retained evidence remains visible. Retry the failed next page.', '取得済みの根拠はそのまま表示されます。失敗した次のページを再取得してください。', '已加载的证据会继续显示。请重新请求失败的下一页。', 'Bằng chứng đã tải vẫn được giữ nguyên. Hãy yêu cầu lại trang tiếp theo bị lỗi.', 'La evidencia ya cargada seguirá visible. Vuelva a solicitar la página siguiente que falló.', 'Bereits geladene Nachweise bleiben sichtbar. Fordern Sie die fehlgeschlagene nächste Seite erneut an.', 'Les éléments de preuve déjà chargés restent visibles. Redemandez la page suivante qui a échoué.'),
    ('Retry the failed next page.', '실패한 다음 페이지를 다시 요청하세요.', 'Retry the failed next page.', '失敗した次のページを再取得してください。', '请重新请求失败的下一页。', 'Hãy yêu cầu lại trang tiếp theo bị lỗi.', 'Vuelva a solicitar la página siguiente que falló.', 'Fordern Sie die fehlgeschlagene nächste Seite erneut an.', 'Redemandez la page suivante qui a échoué.'),
    ('Retry the same query.', '같은 조회를 다시 시도하세요.', 'Retry the same query.', '同じ照会をもう一度実行してください。', '请重试同一查询。', 'Hãy thử lại cùng truy vấn.', 'Vuelva a intentar la misma consulta.', 'Führen Sie dieselbe Abfrage erneut aus.', 'Relancez la même requête.'),
    ('Retry loading earlier VOC', '이전 VOC 더 불러오기 다시 시도', 'Retry loading earlier VOC', '以前のVOCの追加読み込みを再試行', '重试加载更早的VOC', 'Thử tải lại các VOC trước đó', 'Reintentar la carga de VOC anteriores', 'Frühere VOC erneut laden', 'Réessayer le chargement des VOC antérieures'),
    ('Retry Similar VOC', '유사 VOC 다시 조회', 'Retry Similar VOC', '類似VOCを再照会', '重试相似VOC查询', 'Thử lại truy vấn VOC tương tự', 'Reintentar la consulta de VOC similares', 'Ähnliche VOC erneut abfragen', 'Relancer la recherche de VOC similaires'),
    ('Similar VOC evidence is being adjudicated.', '유사 VOC 근거를 판정하고 있습니다.', 'Similar VOC evidence is being adjudicated.', '類似VOCの根拠を判定しています。', '正在判定相似VOC证据。', 'Đang thẩm định bằng chứng VOC tương tự.', 'Se está evaluando la evidencia de VOC similares.', 'Nachweise zu ähnlichen VOC werden bewertet.', 'Les éléments de preuve des VOC similaires sont en cours d’évaluation.'),
    ('No prior VOC was adjudicated as the same issue type.', '같은 문제 유형으로 판정된 과거 VOC가 없습니다.', 'No prior VOC was adjudicated as the same issue type.', '同じ問題タイプと判定された過去のVOCはありません。', '没有被判定为同一问题类型的历史VOC。', 'Không có VOC trước đây nào được xác định là cùng loại vấn đề.', 'No hay VOC anteriores clasificadas como el mismo tipo de problema.', 'Es wurden keine früheren VOC demselben Problemtyp zugeordnet.', 'Aucune VOC antérieure n’a été classée dans le même type de problème.'),
    ('Event time {time}', '사건 시각 {time}', 'Event time {time}', '事象時刻 {time}', '事件时间 {time}', 'Thời điểm sự kiện {time}', 'Hora del evento {time}', 'Ereigniszeit {time}', 'Heure de l’événement {time}'),
    ('Current post evidence', '현재 글 근거', 'Current post evidence', '現在の投稿の根拠', '当前帖子的证据', 'Bằng chứng của bài đăng hiện tại', 'Evidencia de la publicación actual', 'Nachweis aus dem aktuellen Beitrag', 'Élément de preuve de la publication actuelle'),
    ('Prior post evidence', '과거 글 근거', 'Prior post evidence', '過去の投稿の根拠', '历史帖子的证据', 'Bằng chứng của bài đăng trước', 'Evidencia de la publicación anterior', 'Nachweis aus dem früheren Beitrag', 'Élément de preuve de la publication antérieure'),
    ('Customer cohort', '고객군', 'Customer cohort', '顧客群', '客户群', 'Nhóm khách hàng', 'Cohorte de clientes', 'Kundengruppe', 'Cohorte client'),
    ('No same-customer evidence', '동일 고객 근거 없음', 'No same-customer evidence', '同一顧客を示す根拠なし', '无同一客户证据', 'Không có bằng chứng cùng khách hàng', 'No hay evidencia del mismo cliente', 'Kein Nachweis für denselben Kunden', 'Aucun élément de preuve du même client'),
    ('Prior actions', '과거 조치', 'Prior actions', '過去の対応', '历史处置', 'Hành động trước đây', 'Acciones anteriores', 'Frühere Maßnahmen', 'Actions antérieures'),
    ('No recorded action', '기록된 조치 없음', 'No recorded action', '記録された対応なし', '无已记录处置', 'Không có hành động được ghi nhận', 'No hay acciones registradas', 'Keine Maßnahme erfasst', 'Aucune action enregistrée'),
    ('Open evidence post', '근거 글 열기', 'Open evidence post', '根拠となる投稿を開く', '打开证据帖子', 'Mở bài đăng làm bằng chứng', 'Abrir publicación de evidencia', 'Nachweisbeitrag öffnen', 'Ouvrir la publication de preuve'),
    ('Loading earlier VOC...', '이전 VOC를 불러오는 중...', 'Loading earlier VOC...', '以前のVOCを読み込んでいます...', '正在加载更早的VOC...', 'Đang tải các VOC trước đó...', 'Cargando VOC anteriores...', 'Frühere VOC werden geladen...', 'Chargement des VOC antérieures...'),
    ('Show earlier VOC', '이전 VOC 더 보기', 'Show earlier VOC', '以前のVOCをさらに表示', '显示更早的VOC', 'Hiển thị thêm VOC trước đó', 'Mostrar VOC anteriores', 'Weitere frühere VOC anzeigen', 'Afficher davantage de VOC antérieures'),
    ('Retry needed', '다시 시도 필요', 'Retry needed', '再試行が必要です', '需要重试', 'Cần thử lại', 'Es necesario reintentar', 'Erneuter Versuch erforderlich', 'Nouvel essai requis'),
    ('This request failed. Retry the same action.', '요청이 실패했습니다. 같은 작업을 다시 시도하세요.', 'This request failed. Retry the same action.', 'リクエストに失敗しました。同じ操作をもう一度お試しください。', '请求失败。请重试同一操作。', 'Yêu cầu không thành công. Hãy thử lại cùng thao tác.', 'La solicitud falló. Vuelva a intentar la misma acción.', 'Diese Anfrage ist fehlgeschlagen. Wiederholen Sie dieselbe Aktion.', 'La requête a échoué. Réessayez la même action.'),
    ('Could not load more prior VOC. Try again.', '이전 VOC를 더 불러오지 못했습니다. 다시 시도하세요.', 'Could not load more prior VOC. Try again.', '以前のVOCを追加で読み込めませんでした。もう一度お試しください。', '无法加载更多历史VOC。请重试。', 'Không thể tải thêm VOC trước đó. Hãy thử lại.', 'No se pudieron cargar más VOC anteriores. Inténtelo de nuevo.', 'Weitere frühere VOC konnten nicht geladen werden. Versuchen Sie es erneut.', 'Impossible de charger davantage de VOC antérieures. Réessayez.'),
    ('Similar VOC adjudication is unavailable. Try again later.', '유사 VOC 판정을 사용할 수 없습니다. 잠시 후 다시 확인하세요.', 'Similar VOC adjudication is unavailable. Try again later.', '類似VOCの判定を利用できません。しばらくしてからもう一度お試しください。', '相似VOC判定暂不可用。请稍后重试。', 'Tạm thời không thể thẩm định VOC tương tự. Hãy thử lại sau.', 'La evaluación de VOC similares no está disponible. Inténtelo de nuevo más tarde.', 'Die Bewertung ähnlicher VOC ist nicht verfügbar. Versuchen Sie es später erneut.', 'L’évaluation des VOC similaires est indisponible. Réessayez plus tard.');

do $similar_voc_seed$
declare
    owner_state text;
    owner_resource_id bigint;
    target_resource_id bigint;
    expected_key_count integer;
begin
    select ownership_state, resource_id
      into owner_state, owner_resource_id
      from public.ui_translation_seed_ownership
     where migration_key = '0249_z_similar_voc_translation_draft'
       and product_key = 'lineageweave'
       and screen_key = 'similar-voc'
       and resource_version = 1
     for update;

    if owner_state is null then
        raise exception 'Similar VOC translation seed ownership prerequisite is missing';
    end if;

    if owner_state = 'retired' then
        if owner_resource_id is not null then
            raise exception 'Retired Similar VOC seed unexpectedly retains resource %',
                owner_resource_id;
        end if;
        return;
    end if;

    if owner_state = 'blocked' then
        raise exception 'Similar VOC translation seed refuses to adopt an existing unowned resource';
    end if;

    select resource_id
      into target_resource_id
      from public.ui_translation_resource
     where product_key = 'lineageweave'
       and screen_key = 'similar-voc'
       and resource_version = 1
     for update;

    if owner_state = 'owned' then
        if target_resource_id is distinct from owner_resource_id then
            raise exception
                'Similar VOC seed ownership points to resource %, current resource is %',
                owner_resource_id,
                target_resource_id;
        end if;
        -- Review data is mutable while draft. Historical seed bytes no longer
        -- have authority after first materialization, so replay is a no-op.
        return;
    end if;

    if owner_state <> 'pending' then
        raise exception 'Similar VOC translation seed has unexpected ownership state %',
            owner_state;
    end if;

    if target_resource_id is not null then
        raise exception
            'Similar VOC translation seed refuses to adopt existing resource %',
            target_resource_id;
    end if;

    select count(*) into expected_key_count
      from similar_voc_translation_seed;
    if expected_key_count <> 23 then
        raise exception 'Similar VOC translation seed expected 23 keys, found %',
            expected_key_count;
    end if;

    insert into public.ui_translation_resource(product_key, screen_key, resource_version)
    values ('lineageweave', 'similar-voc', 1)
    returning resource_id into target_resource_id;

    if not exists (
        select 1
          from public.ui_translation_seed_ownership
         where migration_key = '0249_z_similar_voc_translation_draft'
           and ownership_state = 'owned'
           and resource_id = target_resource_id
    ) then
        raise exception
            'Similar VOC translation seed did not bind ownership to resource %',
            target_resource_id;
    end if;

    insert into public.ui_translation_key(resource_id, translation_key)
    select target_resource_id, translation_key
      from similar_voc_translation_seed;

    insert into public.ui_translation_text(
        resource_id, translation_key, locale, translated_text
    )
    select
        target_resource_id,
        seed.translation_key,
        localized.locale,
        localized.translated_text
      from similar_voc_translation_seed as seed
      cross join lateral (
          values
              ('ko', seed.ko),
              ('en', seed.en),
              ('ja', seed.ja),
              ('zh', seed.zh),
              ('vi', seed.vi),
              ('es', seed.es),
              ('de', seed.de),
              ('fr', seed.fr)
      ) as localized(locale, translated_text);

    if (
        select count(*)
          from public.ui_translation_key
         where resource_id = target_resource_id
    ) <> expected_key_count
    or (
        select count(*)
          from public.ui_translation_text
         where resource_id = target_resource_id
    ) <> expected_key_count * 8 then
        raise exception 'Similar VOC translation draft failed eight-locale completeness';
    end if;
end;
$similar_voc_seed$;

commit;
