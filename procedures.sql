CREATE PROCEDURE `debugMsg`(IN `enabled` BIT, IN `msg` VARCHAR(255))
    NO SQL
IF enabled THEN SELECT CONCAT('** ',msg) AS '** DEBUG:'; END IF

CREATE PROCEDURE `relatedPosts`(IN `postQid` VARCHAR(20), OUT postList varchar(200) CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci)
BEGIN
    DECLARE sourceList VARCHAR(200) DEFAULT "";
    DECLARE linkLimit INT DEFAULT 5;
    DECLARE keyLimit INT DEFAULT 5;
    SELECT CAST(`value` AS INT) INTO linkLimit FROM settings WHERE `descriptor` = "numlinks";
    SELECT CAST(`value` AS INT) INTO keyLimit FROM settings WHERE `descriptor` = "numkeys";
    
    DROP TABLE IF EXISTS related_posts;
    DROP TABLE IF EXISTS document_keywords;
    CREATE TABLE related_posts (pid VARCHAR(20), tid INT, tfIdf FLOAT);
    CREATE TABLE document_keywords (tokenID int, tfIdf float);
    SET sourceList = tokenList(postQid);

    INSERT INTO related_posts
        SELECT keywords.postID, keywords.tokenID, (tfIdfLog(keywords.tokenID, keywords.postID) * (SELECT document_keywords.tfIdf FROM document_keywords WHERE document_keywords.tokenID = keywords.tokenID)) AS tfIdf
        FROM keywords
        WHERE keywords.tokenID IN
                (SELECT tokenID FROM document_keywords AS source_token_list);

    SELECT GROUP_CONCAT(pid SEPARATOR ',') INTO postList FROM (
    	SELECT pid, (SUM(tfIdf) / keyLimit) as tfIdfAvg FROM related_posts WHERE pid IN (
	    SELECT pid FROM (
	     SELECT pid, COUNT(tid) AS commonKeys
	     FROM related_posts
	     WHERE pid != postQid
	     GROUP BY pid
	     HAVING commonKeys >= FLOOR(keyLimit / 2.0))
	    AS linksWithKeys)
	GROUP BY pid
	ORDER BY tfIdfAvg DESC
	LIMIT linkLimit) AS top_links;
	
    DROP TABLE IF EXISTS document_keywords;
    DROP TABLE IF EXISTS related_posts;
END

CREATE PROCEDURE `queryRelated` (IN `wordList` VARCHAR(2516), OUT postList VARCHAR(20) CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci, OUT outList VARCHAR(2516) CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci)
BEGIN
    DECLARE linkLimit INT DEFAULT 5;
    DECLARE keyLimit INT DEFAULT 5;
    SELECT CAST(`value` AS INT) INTO linkLimit FROM settings WHERE `descriptor` = "numlinks";
    SELECT CAST(`value` AS INT) INTO keyLimit FROM settings WHERE `descriptor` = "numkeys";

    SELECT COUNT(*) INTO @allPosts FROM posts;

    DROP TABLE IF EXISTS query_keys;
    DROP TABLE IF EXISTS rel_posts;
    CREATE TABLE query_keys(tid INT, tfIdf FLOAT);
    CREATE TABLE rel_posts(pid VARCHAR(20), tid INT, tfIdf FLOAT);
    SET @sql = CONCAT("INSERT INTO query_keys (tid) SELECT tokens.id FROM tokens WHERE tokens.token IN (",wordList,");");
    PREPARE stmt FROM @sql;
    EXECUTE stmt;

    UPDATE query_keys SET query_keys.tfIdf = LOG10(1 + (@allPosts / (SELECT tokens.document_count FROM tokens WHERE tokens.id = query_keys.tid)));

    DELETE FROM query_keys WHERE tfIdf < 1;

    SELECT COUNT(*) INTO @numquery FROM query_keys;

    SELECT GROUP_CONCAT(token SEPARATOR ', ') INTO outList FROM (
        SELECT token FROM tokens WHERE id IN (
            SELECT tid FROM query_keys)) AS important_words;

    INSERT INTO rel_posts
        SELECT keywords.postID, keywords.tokenID, (tfIdfLog(keywords.tokenID, keywords.postID) * (SELECT query_keys.tfIdf FROM query_keys WHERE query_keys.tid = keywords.tokenID)) AS tfIdf
        FROM keywords
        WHERE keywords.tokenID IN
            (SELECT tid FROM query_keys AS source_token_list);

    SELECT GROUP_CONCAT(pid SEPARATOR ',') INTO postList FROM (
        SELECT pid, (SUM(tfIdf) / keyLimit) AS tfIdfAvg from rel_posts WHERE pid IN (
            SELECT pid FROM (
                SELECT pid, COUNT(tid) AS commonKeys
                FROM rel_posts
                GROUP BY pid
                HAVING commonKeys = @numquery)
            AS linksWithKeys)
        GROUP BY pid
        ORDER BY tfIdfAvg DESC
        LIMIT linkLimit) as top_links;

    DROP TABLE IF EXISTS query_keys;
    DROP TABLE IF EXISTS rel_posts;
END