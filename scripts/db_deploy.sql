CREATE TABLE `episodes` (
	`series_id` int(11) DEFAULT NULL,
	`season` int(11) DEFAULT NULL,
	`episode` int(11) DEFAULT NULL,
	`title` varchar(50) DEFAULT NULL,
	`airdate` date DEFAULT NULL,
	`description` text,
	UNIQUE KEY `unique_index` (`series_id`,`season`,`episode`)
);

DROP TABLE `series`;
CREATE TABLE `series` (
	`id` int(11) NOT NULL AUTO_INCREMENT,
	`name` varchar(50) DEFAULT NULL,
	`imdb_id` varchar(16) DEFAULT NULL,
	`num_seasons` int(11) DEFAULT 1,
	PRIMARY KEY (`id`),
	UNIQUE KEY `imdb_id` (`imdb_id`)
);

CREATE TABLE `users` (
	`id` int(11) NOT NULL AUTO_INCREMENT,
	`username` varchar(32) NOT NULL,
	`email` text,
	PRIMARY KEY (`id`)
);

insert into users (id, username, email) values(1, "dooz", "magnus.osterlind@gmail.com");
select * from users;

DROP TABLE `user_episodes`;
CREATE TABLE `user_episodes` (
	`user_id` int(11) NOT NULL,
	`series_id` int(11) NOT NULL,
	`season` int(11) NOT NULL,
	`page` int(11) DEFAULT 0,
	`mask` bigint DEFAULT 0,
	UNIQUE KEY `unique_index` (`user_id`,`series_id`,`season`, `page`)
);

select * from series;
select * from episodes where series_id = 1;
select * from user_episodes;