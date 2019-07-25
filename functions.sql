CREATE FUNCTION `keywordList`(`postQid` INT) RETURNS varchar(2560) CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci
BEGIN
  DECLARE finished BIT DEFAULT 0;
  DECLARE keyword INT DEFAULT 0;
  DECLARE keyword_cursor CURSOR FOR SELECT keywords.tokenId FROM keywords WHERE keywords.postId = postQid;
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET finished = 1;
  OPEN keyword_cursor;
  CREATE TEMPORARY TABLE IF NOT EXISTS document_keywords (tokenID int, tfIdf float);
  check_keywords: LOOP
    FETCH keyword_cursor INTO keyword;
    IF finished = 1 THEN LEAVE check_keywords; END IF;
    SET @tf_idf = tfIdfScore(keyword, postQid);
    INSERT INTO document_keywords VALUES (keyword, @tf_idf);
  END LOOP check_keywords;
  CLOSE keyword_cursor;
  SELECT GROUP_CONCAT(token SEPARATOR ', ') INTO @output FROM (SELECT tokens.token,document_keywords.tfIdf FROM tokens INNER JOIN document_keywords ON tokens.id = document_keywords.tokenID ORDER BY document_keywords.tfIdf DESC LIMIT 5) as s1;
  DROP TEMPORARY TABLE document_keywords;
  RETURN @output;
END

CREATE FUNCTION `tfIdfScore`(`tokenQid` INT, `postQid` INT) RETURNS float
RETURN
    (SELECT keywords.num_in_post
        FROM keywords
        WHERE keywords.tokenId = tokenQid 
            AND keywords.postId = postQid
        LIMIT 1)
    *
    (LOG10(
        (SELECT COUNT(*) FROM posts)
        /
        (SELECT tokens.document_count
            FROM tokens
            WHERE tokens.id = tokenQid
            LIMIT 1)
    ))

CREATE FUNCTION `tokenList`(`postQid` VARCHAR(20)) RETURNS varchar(2560) CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci
BEGIN
  DECLARE finished BIT DEFAULT 0;
  DECLARE keyword INT DEFAULT 0;
  DECLARE keyword_cursor CURSOR FOR SELECT keywords.tokenId FROM keywords WHERE keywords.postId = postQid;
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET finished = 1;
  OPEN keyword_cursor;
  CREATE TEMPORARY TABLE IF NOT EXISTS document_keywords (tokenID int, tfIdf float);
  check_keywords: LOOP
    FETCH keyword_cursor INTO keyword;
    IF finished = 1 THEN LEAVE check_keywords; END IF;
    SET @tf_idf = tfIdfScore(keyword, postQid);
    INSERT INTO document_keywords VALUES (keyword, @tf_idf);
  END LOOP check_keywords;
  CLOSE keyword_cursor;
  SELECT GROUP_CONCAT(id SEPARATOR ',') INTO @output FROM (SELECT tokens.id,document_keywords.tfIdf FROM tokens INNER JOIN document_keywords ON tokens.id = document_keywords.tokenID ORDER BY document_keywords.tfIdf DESC LIMIT 5) as s1;
  RETURN @output;
END

CREATE FUNCTION `tfIdfAlternate`(`tokenQid` INT, `postQid` VARCHAR(20)) RETURNS float
RETURN
    ((SELECT keywords.num_in_post
        FROM keywords
        WHERE keywords.tokenId = tokenQid
            AND keywords.postId = postQid
        LIMIT 1)
     /
     (SELECT SUM(keywords.num_in_post)
        FROM keywords
        WHERE keywords.postId = postQid)
    )
    *
    (LOG10(
        (SELECT COUNT(*) FROM posts)
        /
        (SELECT tokens.document_count
            FROM tokens
            WHERE tokens.id = tokenQid
            LIMIT 1)
    ))

CREATE FUNCTION `tfIdf3`(`tokenQid` INT, `postQid` VARCHAR(20)) RETURNS float
RETURN
    (0.5 +
     (0.5 *
      ((SELECT keywords.num_in_post
        FROM keywords
        WHERE keywords.tokenId = tokenQid
            AND keywords.postId = postQid
        LIMIT 1) /
       (SELECT MAX(num_in_post)
        FROM keywords
        WHERE postId = postQid))))
    *
    (LOG10(
        (SELECT COUNT(*) FROM posts)
        /
        (SELECT tokens.document_count
            FROM tokens
            WHERE tokens.id = tokenQid
            LIMIT 1)
    ))

CREATE FUNCTION `relatedPosts`(`postQid` VARCHAR(20)) RETURNS varchar(200) CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci
BEGIN
    DECLARE numTokens INT DEFAULT 0;
    DECLARE postList VARCHAR(200) DEFAULT "";
    DECLARE sourceList VARCHAR(200) DEFAULT "";
    SET sourceList = tokenList(postQid);
    SET numTokens = LENGTH(sourceList) - LENGTH(REPLACE(sourceList,',','')) + 1;
    SET @myNum = numTokens;
    CREATE TEMPORARY TABLE IF NOT EXISTS source_tokens (tid INT);
    SET @myTokens = sourceList;
    get_tokens: LOOP
        IF @myNum = 0 OR LENGTH(@myTokens) = 0 THEN LEAVE get_tokens; END IF;
        INSERT INTO source_tokens VALUES (CAST(SUBSTRING_INDEX(@myTokens,',',1) AS INT));
        SET @myNum = @myNum - 1;
        SET @myTokens = SUBSTRING_INDEX(@myTokens,',',-@myNum);
    END LOOP get_tokens;

    CREATE TEMPORARY TABLE IF NOT EXISTS related_posts (pid VARCHAR(20), tid INT, tfIdf FLOAT);

    INSERT INTO related_posts
        SELECT keywords.postID, keywords.tokenID, tfIdfScore(keywords.tokenID, keywords.postID) AS tfIdf
        FROM keywords
        WHERE keywords.tokenID IN
                (SELECT tid FROM source_tokens AS source_token_list);

    SELECT GROUP_CONCAT(pid SEPARATOR ',') INTO postList FROM (SELECT pid, AVG(tfIdf) as tfIdfAvg FROM related_posts WHERE pid != postQid GROUP BY pid ORDER BY tfIdfAvg DESC LIMIT 5) AS top_five;
	DROP TEMPORARY TABLE source_tokens;
    DROP TEMPORARY TABLE related_posts;
    RETURN postList;
END
