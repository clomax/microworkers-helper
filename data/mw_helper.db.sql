BEGIN TRANSACTION;
CREATE TABLE `user` (
	`balance`	TEXT DEFAULT '$0.00'
);
CREATE TABLE settings (
	ttl	INTEGER NOT NULL DEFAULT 5
);
CREATE TABLE `log` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	`text`	TEXT NOT NULL,
	`error`	INTEGER DEFAULT 0
);
CREATE TABLE "jobs" (
	`id`	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
	`name`	TEXT NOT NULL,
	`pay`	REAL NOT NULL,
	`url`	TEXT NOT NULL UNIQUE,
	`hidden`	INTEGER DEFAULT 0
);
CREATE TABLE "filter" (
	`id`	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
	`string`	TEXT UNIQUE
);
COMMIT;
