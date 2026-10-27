-- 仅移除物理外键；保留关联字段、主键、唯一约束及普通索引。
-- MySQL 的 ALTER TABLE 会隐式提交，执行前应备份并核对目标数据库。
ALTER TABLE `ai_chat` DROP FOREIGN KEY `fk_ai_chat_user`;
ALTER TABLE `favorite` DROP FOREIGN KEY `fk_favorite_news`;
ALTER TABLE `favorite` DROP FOREIGN KEY `fk_favorite_user`;
ALTER TABLE `history` DROP FOREIGN KEY `fk_history_news`;
ALTER TABLE `history` DROP FOREIGN KEY `fk_history_user`;
ALTER TABLE `news` DROP FOREIGN KEY `fk_news_category`;
ALTER TABLE `related_news` DROP FOREIGN KEY `fk_related_news_news`;
ALTER TABLE `related_news` DROP FOREIGN KEY `fk_related_news_related`;
ALTER TABLE `user_token` DROP FOREIGN KEY `fk_user_token_user`;
