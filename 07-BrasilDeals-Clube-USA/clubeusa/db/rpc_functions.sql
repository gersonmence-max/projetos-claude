-- ============================================================
--  rpc_functions.sql — Funcoes RPC do Supabase
--  Operacoes atomicas que o cliente pode chamar com seguranca
-- ============================================================

-- Incrementar pontos (atomico, evita race condition)
CREATE OR REPLACE FUNCTION increment_points(p_member_id UUID, p_points INTEGER)
RETURNS void AS $$
BEGIN
    UPDATE members SET points = points + p_points WHERE id = p_member_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Incrementar cliques
CREATE OR REPLACE FUNCTION increment_clicks(p_member_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE members SET total_clicks = total_clicks + 1 WHERE id = p_member_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Incrementar contador de indicacoes
CREATE OR REPLACE FUNCTION increment_referral_count(p_member_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE members SET referral_count = referral_count + 1 WHERE id = p_member_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Candidatos ao sorteio da semana (quem clicou ao menos 1x)
CREATE OR REPLACE FUNCTION get_raffle_candidates(p_week_start DATE, p_plan VARCHAR)
RETURNS TABLE(member_id UUID, click_count BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT c.member_id, COUNT(c.id) as click_count
    FROM clicks c
    JOIN members m ON m.id = c.member_id
    WHERE c.clicked_at >= p_week_start
      AND c.clicked_at <  p_week_start + INTERVAL '7 days'
      AND m.plan = p_plan
      AND m.status = 'active'
      AND m.deleted_at IS NULL
    GROUP BY c.member_id
    HAVING COUNT(c.id) >= 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Top membros por pontos (ranking)
CREATE OR REPLACE FUNCTION get_leaderboard(p_limit INTEGER DEFAULT 10)
RETURNS TABLE(
    rank BIGINT, member_id UUID,
    points INTEGER, level VARCHAR, referral_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ROW_NUMBER() OVER (ORDER BY m.points DESC) as rank,
        m.id, m.points, m.level, m.referral_count
    FROM members m
    WHERE m.status = 'active' AND m.deleted_at IS NULL
    ORDER BY m.points DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
