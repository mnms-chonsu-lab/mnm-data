-- 시연용 데모 데이터 (명세 REQ-DATA-06): 김한우 농장(448012)의 소·일지·출생 신고 초안·알림·동의 기록 + 접수자 웹 접수 기록 4건
-- 값은 화면 가짜 데이터(mnm-frontend packages/mocks)와 같게 맞추고, 거기 없는 값은 엑셀 v2(촌수의사_시연_더미데이터_v2.xlsx)를 따른다.
-- 이름·번호는 모두 가상이다.
-- 계정·농장·기관은 mnm-dev R__seed_demo_accounts.sql 이 먼저 넣는다. 이 파일은 그 뒤에 실행한다.
-- 날짜는 실행일(CURRENT_DATE) 기준으로 넣는다. 시연일에도 "최근 14일 일지"가 채워져 보이게 하려는 것.
-- 여러 번 실행해도 중복으로 들어가지 않는다. 등록 시연용 농가(499902·499904)에는 아무것도 넣지 않는다.
-- 사진·음성 파일은 Object Storage demo/ 에 올리고, 이 파일은 그 경로만 연결한다 (8·9번).

BEGIN;
-- 날짜 기준을 한국 시각으로 고정 (이 실행 안에서만 적용, DB 설정은 안 바뀜)
SET LOCAL TIME ZONE 'Asia/Seoul';

-- 1) 김한우 농장 위치 (가까운 거점소독시설 찾기용)
UPDATE farm_info SET region_code = '4480025000', lat = 36.6013, lng = 126.6608
WHERE farm_no = '448012';

-- 2) 소 3마리 + 끝 4자리 겹침 소 1마리 (유민님 요청, mnm-dev#40)
--    3마리는 화면 프로토타입(packages/mocks)과 같게 이력제 조회로 등록한 소(source = 'trace')
--    겹침 소는 엑셀 v2 값 그대로 직접 입력(source = 'manual', 접종 기록 없음)
INSERT INTO cows (farm_id, tag_last4, tag_full, breed, sex, birth_date, vaccine_last_date, vaccine_last_order, barn, status, source, trace_farm_no, trace_checked_at)
SELECT f.farm_id, right(v.tag, 4), v.tag, '한우', v.sex, v.birth::date, v.vac::date, v.vac_order, v.barn, 'active', v.src,
       CASE WHEN v.src = 'trace' THEN f.farm_no END,
       CASE WHEN v.src = 'trace' THEN now() - interval '30 days' END
FROM farm_info f, (VALUES
  ('002123451234', '암', '2022-03-14', '2026-04-02', 7,    '2번 축사', 'trace'),
  ('002123450871', '암', '2020-03-14', '2026-04-02', 7,    '1번 축사', 'trace'),
  ('002123455520', '수', '2024-03-14', '2026-04-02', 7,    '3번 축사', 'trace'),
  -- 끝 4자리 겹침 테스트용 (mnm-ai #6)
  ('002123460871', '암', '2020-03-15', NULL,         NULL, '2번 축사', 'manual')
) AS v(tag, sex, birth, vac, vac_order, barn, src)
WHERE f.farm_no = '448012'
ON CONFLICT ON CONSTRAINT uk_cows_farm_tag DO NOTHING;

-- 3) 최근 14일 일지 (d = 며칠 전). 이 농가 일지가 하나도 없을 때만 넣는다
INSERT INTO diary_entry (farm_id, date, category, cow_id, value, vaccine_type, head_count, raw_text)
SELECT f.farm_id, CURRENT_DATE - v.d, v.category, c.cow_id, v.value, v.vaccine_type, v.head_count, v.raw_text
FROM farm_info f
CROSS JOIN (VALUES
  (13, '사육현황', NULL,           '총 42두',            NULL,     42,        '오늘 우리 소 마흔두 마리 다 있어'),
  (13, '소독',     NULL,           '축사 소독',          NULL,     NULL::int, '축사 소독했어'),
  (12, '관찰',     '002123450871', '사료 잘 먹음',       NULL,     NULL::int, '0871번 사료 잘 먹었어'),
  (11, '출입',     NULL,           '사료 차량 출입',     NULL,     NULL::int, '사료 차 들어왔다 갔어'),
  (10, '소독',     NULL,           '축사 소독',          NULL,     NULL::int, '축사 소독했어'),
  (10, '접종',     '002123451234', '백신',               '구제역', NULL::int, '1234번 구제역 주사 놨어'),
  ( 9, '메모',     NULL,           '볏짚 들여옴',        NULL,     NULL::int, '볏짚 들여놨어'),
  ( 8, '관찰',     '002123455520', '특이사항 없음',      NULL,     NULL::int, '5520번은 별일 없어'),
  ( 7, '소독',     NULL,           '축사 소독',          NULL,     NULL::int, '축사 소독했어'),
  ( 7, '관찰',     '002123460871', '특이사항 없음',      NULL,     NULL::int, '2번 축사 0871번은 별일 없어'),
  ( 6, '사육현황', NULL,           '총 42두',            NULL,     42,        '마흔두 마리 그대로야'),
  ( 5, '출입',     NULL,           '사료 차량 출입',     NULL,     NULL::int, '사료 차 다녀갔어'),
  ( 5, '관찰',     '002123451234', '사료 잘 먹음',       NULL,     NULL::int, '1234번 사료 잘 먹었어'),
  ( 4, '관찰',     '002123450871', '배가 많이 불러옴',   NULL,     NULL::int, '0871번 배가 많이 불렀어'),
  ( 4, '소독',     NULL,           '축사 소독',          NULL,     NULL::int, '축사 소독했어'),
  ( 3, '관찰',     '002123451234', '사료 조금 남김',     NULL,     NULL::int, '1234번이 사료를 남겼어'),
  ( 2, '출입',     NULL,           '사료 차량 출입',     NULL,     NULL::int, '사료 차 들어왔어'),
  ( 1, '소독',     NULL,           '축사 소독',          NULL,     NULL::int, '축사 소독했어'),
  ( 1, '관찰',     '002123460871', '사료 잘 먹음',       NULL,     NULL::int, '2번 축사 0871번 사료 잘 먹었어'),
  ( 0, '소독',     NULL,           '2번 축사',           NULL,     NULL::int, '아침에 2번 축사 소독했고, 1234번이 사료를 좀 남겼어.'),
  ( 0, '관찰',     '002123451234', '사료 남김',          NULL,     NULL::int, '아침에 2번 축사 소독했고, 1234번이 사료를 좀 남겼어.'),
  ( 0, '관찰',     '002123455520', '특이사항 없음',      NULL,     NULL::int, '5520번은 괜찮아')
) AS v(d, category, tag, value, vaccine_type, head_count, raw_text)
LEFT JOIN cows c ON c.tag_full = v.tag AND c.farm_id = (SELECT farm_id FROM farm_info WHERE farm_no = '448012')
WHERE f.farm_no = '448012'
  AND NOT EXISTS (SELECT 1 FROM diary_entry e WHERE e.farm_id = f.farm_id);

-- 4) 출생 신고 초안 (어제 태어난 0871번 송아지). 기한 = 출생일 다음 날부터 토·일·공휴일 빼고 5일째 (서버 FarmerRules.reportDue 와 같은 규칙)
INSERT INTO history_report (farm_id, type, fields, missing, due_date, mode, status)
SELECT f.farm_id, '출생',
       jsonb_build_object('mother_tag4', '0871', 'birth_date', to_char(CURRENT_DATE - 1, 'YYYY-MM-DD'), 'sex', '암', 'breed', '한우'),
       '[]'::jsonb,
       (SELECT d::date FROM (
          SELECT d, row_number() OVER (ORDER BY d) AS n
          FROM generate_series(CURRENT_DATE, CURRENT_DATE + 30, interval '1 day') AS d
          WHERE extract(isodow FROM d) < 6 AND d::date NOT IN (SELECT date FROM holidays)
        ) w WHERE n = 5),
       NULL, 'draft'
FROM farm_info f
WHERE f.farm_no = '448012'
  AND NOT EXISTS (SELECT 1 FROM history_report h WHERE h.farm_id = f.farm_id);

-- 4-1) 그 신고의 기한 할 일 (앱이 초안을 만들 때 같이 만드는 것과 같음)
INSERT INTO tasks (farm_id, kind, title, due_date, ref_id)
SELECT h.farm_id, 'birth_report', '송아지 출생 신고', h.due_date, h.history_report_id
FROM history_report h JOIN farm_info f ON f.farm_id = h.farm_id
WHERE f.farm_no = '448012' AND h.type = '출생' AND h.status = 'draft'
  AND NOT EXISTS (SELECT 1 FROM tasks t WHERE t.kind = 'birth_report' AND t.ref_id = h.history_report_id);

-- 5) 알림 2건 (농장주에게)
-- ① 평소와 다름: 1234번이 3일 전과 오늘 사료를 남김
INSERT INTO alerts (users_id, kind, title, body, ref_id, created_at)
SELECT f.owner_user_id, 'diff', '1234번, 평소와 다른 모습이 보여요',
       to_char(CURRENT_DATE - 3, 'FMMM"월" FMDD"일"') || '과 ' || to_char(CURRENT_DATE, 'FMMM"월" FMDD"일"')
         || '에 사료 남김을 기록했어요. 한 번 살펴봐 주세요.',
       c.cow_id, now()
FROM farm_info f JOIN cows c ON c.farm_id = f.farm_id AND c.tag_full = '002123451234'
WHERE f.farm_no = '448012'
  AND NOT EXISTS (SELECT 1 FROM alerts a WHERE a.users_id = f.owner_user_id AND a.kind = 'diff');

-- ② 신고 기한: 송아지 출생 신고
INSERT INTO alerts (users_id, kind, title, body, ref_id, created_at)
SELECT f.owner_user_id, 'deadline', '송아지 출생 신고 · ' || (t.due_date - CURRENT_DATE) || '일 남음', NULL, t.tasks_id, now()
FROM farm_info f JOIN tasks t ON t.farm_id = f.farm_id AND t.kind = 'birth_report' AND t.done_at IS NULL
WHERE f.farm_no = '448012'
  AND NOT EXISTS (SELECT 1 FROM alerts a WHERE a.users_id = f.owner_user_id AND a.kind = 'deadline');

-- 6) 동의 기록 3건 (김한우 농장주). 종류는 로그인 API(AUTH-01)와 같은 privacy·delivery·outsourcing. 버전은 제안값
INSERT INTO consents (users_id, consent_type, version, agreed_at)
SELECT f.owner_user_id, v.consent_type, 'v1', now() - interval '30 days'
FROM farm_info f, (VALUES ('privacy'), ('delivery'), ('outsourcing')) AS v(consent_type)
WHERE f.farm_no = '448012'
  AND NOT EXISTS (SELECT 1 FROM consents c WHERE c.users_id = f.owner_user_id AND c.consent_type = v.consent_type);

-- 7) 접수 기록 4건 (접수자 웹 수신함, 홍성축협). 화면 가짜 데이터의 4줄과 같은 순서로 보이게 한다
--   ① 김한우 농장 1234번 소 상태 기록 · 전화 · 새로 옴
--   ② 송아지목장(499901) 0871번 소 상태 기록 · 축협 · 확인 중
--   ③ 솔밭농장(499905) 출생 신고 · 축협 · 새로 옴
--   ④ 들판한우(499903) 5520번 소 상태 기록 · 웹 · 처리 완료(수의사 진료 안내)
-- 수신함은 번호가 큰 것부터 보이므로 ④ → ① 순서로 넣는다. 시각은 화면 가짜 데이터와 같은 한국 시각
-- 등록 시연용 농가(499902·499904)와 테스트 농가(499906)에는 넣지 않는다
-- 이미 넣었으면(전달 키 seed-demo-1 이 있으면) 건너뛴다
INSERT INTO cows (farm_id, tag_last4, tag_full, breed, sex, birth_date, vaccine_last_date, vaccine_last_order, barn, status, source, trace_farm_no, trace_checked_at)
SELECT f.farm_id, right(v.tag, 4), v.tag, '한우', v.sex, v.birth::date, '2026-04-02', 7, v.barn, 'active', 'trace', f.farm_no, now() - interval '30 days'
FROM farm_info f JOIN (VALUES
  ('499901', '002198760871', '암', '2020-03-14', '1번 축사'),
  ('499903', '002198765520', '수', '2024-03-14', '3번 축사')
) AS v(farm_no, tag, sex, birth, barn) ON v.farm_no = f.farm_no
ON CONFLICT ON CONSTRAINT uk_cows_farm_tag DO NOTHING;

DO $$
DECLARE
  coop    BIGINT := (SELECT org_id FROM receiver_org WHERE name = '홍성축협' ORDER BY org_id LIMIT 1);
  checker BIGINT := (SELECT users_id FROM users WHERE login_id = 'hs-bio');
  sr BIGINT; rs BIGINT; hr BIGINT; dl BIGINT;
BEGIN
  IF EXISTS (SELECT 1 FROM deliveries WHERE idempotency_key LIKE 'seed-demo-%') THEN
    RETURN;
  END IF;

  -- ④ 들판한우 5520번 · 웹 · 처리 완료
  INSERT INTO symptom_report (farm_id, cow_id, answers, matched_count, found_at, barn)
  SELECT f.farm_id, c.cow_id, '{"drool":"yes","blister":"no","feed":"yes","lump":"no"}', 2,
         (CURRENT_DATE - 1 + time '16:00') AT TIME ZONE 'Asia/Seoul', c.barn
  FROM farm_info f JOIN cows c ON c.farm_id = f.farm_id AND c.tag_full = '002198765520'
  WHERE f.farm_no = '499903' RETURNING symptom_report_id INTO sr;
  INSERT INTO report_summary (symptom_report_id) VALUES (sr) RETURNING report_summary_id INTO rs;
  INSERT INTO deliveries (report_summary_id, route, org_id, cc_org_id, share_phone, idempotency_key, approved_at, received_at, status)
  VALUES (rs, 'web', NULL, coop, TRUE, 'seed-demo-4',
          (CURRENT_DATE - 1 + time '17:20') AT TIME ZONE 'Asia/Seoul',
          (CURRENT_DATE - 1 + time '17:20') AT TIME ZONE 'Asia/Seoul', 'delivered')
  RETURNING deliveries_id INTO dl;
  INSERT INTO receiver_check (deliveries_id, org_id, users_id, status, result, at)
  VALUES (dl, coop, checker, 'done', 'vet_guide', (CURRENT_DATE - 1 + time '18:00') AT TIME ZONE 'Asia/Seoul');

  -- ③ 솔밭농장 출생 신고 · 축협 · 새로 옴 (김한우 농장의 초안과 겹치지 않게 다른 농가로 둔다)
  INSERT INTO history_report (farm_id, type, fields, missing, due_date, mode, status)
  SELECT f.farm_id, '출생',
         jsonb_build_object('mother_tag4', '0871', 'birth_date', to_char(CURRENT_DATE - 1, 'YYYY-MM-DD'), 'sex', '암', 'breed', '한우'),
         '[]'::jsonb,
         (SELECT d::date FROM (
            SELECT d, row_number() OVER (ORDER BY d) AS n
            FROM generate_series(CURRENT_DATE, CURRENT_DATE + 30, interval '1 day') AS d
            WHERE extract(isodow FROM d) < 6 AND d::date NOT IN (SELECT date FROM holidays)
          ) w WHERE n = 5),
         'coop', 'sent'
  FROM farm_info f WHERE f.farm_no = '499905' RETURNING history_report_id INTO hr;
  INSERT INTO deliveries (history_report_id, route, org_id, cc_org_id, share_phone, idempotency_key, approved_at, received_at, status)
  VALUES (hr, 'coop', coop, NULL, TRUE, 'seed-demo-3',
          (CURRENT_DATE - 1 + time '20:10') AT TIME ZONE 'Asia/Seoul',
          (CURRENT_DATE - 1 + time '20:10') AT TIME ZONE 'Asia/Seoul', 'delivered');

  -- ② 송아지목장 0871번 · 축협 · 확인 중
  INSERT INTO symptom_report (farm_id, cow_id, answers, matched_count, found_at, barn)
  SELECT f.farm_id, c.cow_id, '{"drool":"yes","blister":"no","feed":"yes","lump":"no"}', 2,
         (CURRENT_DATE + time '07:30') AT TIME ZONE 'Asia/Seoul', c.barn
  FROM farm_info f JOIN cows c ON c.farm_id = f.farm_id AND c.tag_full = '002198760871'
  WHERE f.farm_no = '499901' RETURNING symptom_report_id INTO sr;
  INSERT INTO report_summary (symptom_report_id) VALUES (sr) RETURNING report_summary_id INTO rs;
  INSERT INTO deliveries (report_summary_id, route, org_id, cc_org_id, share_phone, idempotency_key, approved_at, received_at, status)
  VALUES (rs, 'coop', coop, NULL, TRUE, 'seed-demo-2',
          (CURRENT_DATE + time '08:15') AT TIME ZONE 'Asia/Seoul',
          (CURRENT_DATE + time '08:15') AT TIME ZONE 'Asia/Seoul', 'delivered')
  RETURNING deliveries_id INTO dl;
  INSERT INTO receiver_check (deliveries_id, org_id, users_id, status, at)
  VALUES (dl, coop, checker, 'checking', (CURRENT_DATE + time '08:40') AT TIME ZONE 'Asia/Seoul');

  -- ① 김한우 농장 1234번 · 전화(함께 받는 축협) · 새로 옴
  INSERT INTO symptom_report (farm_id, cow_id, answers, matched_count, found_at, barn)
  SELECT f.farm_id, c.cow_id, '{"drool":"yes","blister":"no","feed":"yes","lump":"no"}', 2,
         (CURRENT_DATE + time '08:00') AT TIME ZONE 'Asia/Seoul', c.barn
  FROM farm_info f JOIN cows c ON c.farm_id = f.farm_id AND c.tag_full = '002123451234'
  WHERE f.farm_no = '448012' RETURNING symptom_report_id INTO sr;
  INSERT INTO report_summary (symptom_report_id) VALUES (sr) RETURNING report_summary_id INTO rs;
  INSERT INTO deliveries (report_summary_id, route, org_id, cc_org_id, share_phone, idempotency_key, approved_at, received_at, status)
  VALUES (rs, 'call', NULL, coop, TRUE, 'seed-demo-1',
          (CURRENT_DATE + time '09:42') AT TIME ZONE 'Asia/Seoul',
          (CURRENT_DATE + time '09:42') AT TIME ZONE 'Asia/Seoul', 'delivered');
END $$;

-- 8) 데모 사진: 소 상태 기록 3건(①②④)에 입·몸 옆면 사진 연결 (Object Storage demo/, 출처는 PR에)
--    ③ 솔밭농장은 출생 신고라 사진 없음
INSERT INTO field_media (symptom_report_id, kind, requested_part, predicted_part, match, file_path)
SELECT s.symptom_report_id, 'photo', p.part, p.part, TRUE, p.path
FROM deliveries d
JOIN report_summary s ON s.report_summary_id = d.report_summary_id
CROSS JOIN (VALUES ('mouth', 'demo/photo/mouth.jpg'),
                   ('flank', 'demo/photo/side.jpg')) AS p(part, path)
WHERE d.idempotency_key IN ('seed-demo-1', 'seed-demo-2', 'seed-demo-4')
  AND NOT EXISTS (SELECT 1 FROM field_media m
                  WHERE m.symptom_report_id = s.symptom_report_id AND m.file_path = p.path);

-- 9) 데모 음성: 오늘 일지(2번 축사 소독 · 1234번 사료 남김)에 연결
WITH a AS (
  INSERT INTO field_media (kind, file_path)
  SELECT 'audio', 'demo/audio/diary_today.m4a'
  WHERE NOT EXISTS (SELECT 1 FROM field_media WHERE file_path = 'demo/audio/diary_today.m4a')
  RETURNING media_id
)
UPDATE diary_entry e SET audio_media_id = a.media_id
FROM a, farm_info f
WHERE f.farm_id = e.farm_id AND f.farm_no = '448012'
  AND e.date = CURRENT_DATE AND e.raw_text LIKE '아침에 2번 축사 소독했고%';

COMMIT;

-- 확인
SELECT tag_last4, tag_full, sex, birth_date, barn FROM cows c JOIN farm_info f USING (farm_id) WHERE f.farm_no = '448012' ORDER BY tag_full;
SELECT count(*) AS 일지, count(DISTINCT date) AS 일수, min(date) AS 처음, max(date) AS 마지막 FROM diary_entry e JOIN farm_info f USING (farm_id) WHERE f.farm_no = '448012';
SELECT type, status, fields, due_date FROM history_report h JOIN farm_info f USING (farm_id) WHERE f.farm_no = '448012';
SELECT kind, title, due_date FROM tasks t JOIN farm_info f USING (farm_id) WHERE f.farm_no = '448012';
SELECT a.kind, a.title, a.body FROM alerts a JOIN farm_info f ON f.owner_user_id = a.users_id WHERE f.farm_no = '448012';
SELECT c.consent_type, c.version FROM consents c JOIN farm_info f ON f.owner_user_id = c.users_id WHERE f.farm_no = '448012';
SELECT d.deliveries_id, d.idempotency_key, d.route, coalesce(fs.name, fh.name) AS 농가, cw.tag_last4,
       coalesce((SELECT rc.status FROM receiver_check rc WHERE rc.deliveries_id = d.deliveries_id ORDER BY rc.receiver_check_id DESC LIMIT 1), 'new') AS 상태,
       d.approved_at AT TIME ZONE 'Asia/Seoul' AS 승인_한국시각
FROM deliveries d
LEFT JOIN report_summary s ON s.report_summary_id = d.report_summary_id
LEFT JOIN symptom_report sr ON sr.symptom_report_id = s.symptom_report_id
LEFT JOIN farm_info fs ON fs.farm_id = sr.farm_id
LEFT JOIN cows cw ON cw.cow_id = sr.cow_id
LEFT JOIN history_report h ON h.history_report_id = d.history_report_id
LEFT JOIN farm_info fh ON fh.farm_id = h.farm_id
WHERE d.idempotency_key LIKE 'seed-demo-%' ORDER BY d.deliveries_id DESC;
SELECT m.media_id, m.kind, m.requested_part, m.file_path FROM field_media m WHERE m.file_path LIKE 'demo/%' ORDER BY m.media_id;
