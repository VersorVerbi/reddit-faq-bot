CREATE FUNCTION `keywordList`(`postQid` INT) RETURNS varchar(2560) CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci
BEGIN
  DECLARE finished BIT DEFAULT 0;
  DECLARE keyword INT DEFAULT 0;
  DECLARE keyword_cursor CURSOR FOR SELECT keywords.tokenId FROM keywords WHERE keywords.postId = postQid;
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET finished = 1;
  OPEN keyword_cursor;
  check_keywords: LOOP
    FETCH keyword_cursor INTO keyword;
    IF finished = 1 THEN LEAVE check_keywords; END IF;
    SET @tf_idf = tfIdfScore(keyword, postQid);
    IF @tf_idf > 5 THEN
      SELECT tokens.token FROM tokens WHERE tokens.id = keyword LIMIT 1 INTO @str;
      SET @output = CONCAT(@output,";",@str);
    END IF;
  END LOOP check_keywords;
  CLOSE keyword_cursor;
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
        *
        (SELECT tokens.document_count
            FROM tokens
            WHERE tokens.id = tokenQid
            LIMIT 1)
    ))