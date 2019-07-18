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
