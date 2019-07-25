CREATE PROCEDURE `closestMatch`(
    IN `inTokenString` VARCHAR(512),
    OUT `matchString` VARCHAR(512),
    OUT `matchId` INT,
    OUT `matchProximity` FLOAT)
BEGIN
    DECLARE finished BIT DEFAULT 0;
    DECLARE token_string VARCHAR(512) DEFAULT "";
    DECLARE token_id INT DEFAULT 0;
    DECLARE max_jac FLOAT DEFAULT 0;
    DECLARE max_id INT DEFAULT 0;
    DECLARE max_string VARCHAR(512) DEFAULT "";

    DECLARE token_cursor CURSOR FOR SELECT tokens.id, tokens.token FROM tokens;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET finished = 1;

    OPEN token_cursor;

    fuzzy_match: LOOP
        FETCH token_cursor INTO token_id, token_string;
        IF finished = 1 THEN LEAVE fuzzy_match; END IF;
        CALL jaccardScore(inTokenString, token_string, @jac);
        IF @jac > max_jac THEN
                SET max_jac = @jac;
            SET max_id = token_id;
            SET max_string = token_string;
        END IF;
    END LOOP fuzzy_match;
    SET matchString = max_string;
    SET matchId = max_id;
    SET matchProximity = max_jac;
END


CREATE PROCEDURE `jaccardScore`(
    IN `token1` VARCHAR(512),
    IN `token2` VARCHAR(512),
    OUT `score` FLOAT)
BEGIN
        DECLARE split_length INT DEFAULT 0;
        SET @split1 = GREATEST(1,LEAST(3, FLOOR(CHAR_LENGTH(token1) / 3)));
    SET @split2 = GREATEST(1,LEAST(3, FLOOR(CHAR_LENGTH(token2) / 3)));
    SET split_length = LEAST(@split1, @split2);

    DROP TABLE IF EXISTS token_1_chunks;
    DROP TABLE IF EXISTS token_2_chunks;
    CREATE TEMPORARY TABLE IF NOT EXISTS token_1_chunks (idx INT, chunk VARCHAR(3));
    CREATE TEMPORARY TABLE IF NOT EXISTS token_2_chunks (idx INT, chunk VARCHAR(3));

    SET @i = 1;
    SET @idx = 0;
    get_chunks_1: LOOP
        IF @i > CHAR_LENGTH(token1) THEN LEAVE get_chunks_1; END IF;
        SET @chunk = SUBSTRING(token1, @i, split_length);
        INSERT INTO token_1_chunks VALUES (@idx, @chunk);
        SET @idx = @idx + 1;
        SET @i = @i + 1;
    END LOOP get_chunks_1;

    SET @i = 1;
    SET @idx = 0;
    get_chunks_2: LOOP
        IF @i > CHAR_LENGTH(token2) THEN LEAVE get_chunks_2; END IF;
        SET @chunk = SUBSTRING(token2, @i, split_length);
        INSERT INTO token_2_chunks VALUES (@idx, @chunk);
        SET @idx = @idx + 1;
        SET @i = @i + 1;
    END LOOP get_chunks_2;

    SELECT @intersect_count:=COUNT(*) FROM token_1_chunks t1 INNER JOIN token_2_chunks t2 ON t1.chunk = t2.chunk;
    SELECT @union_count:=COUNT(*) FROM (SELECT t1.chunk FROM token_1_chunks t1 UNION (SELECT t2.chunk FROM token_2_chunks t2)) AS s1;

    SET score:=(@intersect_count / @union_count);
END


CREATE PROCEDURE `debugMsg`(IN `enabled` BIT, IN `msg` VARCHAR(255))
    NO SQL
IF enabled THEN SELECT CONCAT('** ',msg) AS '** DEBUG:'; END IF