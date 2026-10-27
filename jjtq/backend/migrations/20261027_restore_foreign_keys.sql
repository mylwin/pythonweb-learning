-- 恢复移除前的外键和级联规则；若存在孤儿记录，必须先处理后再执行。
-- MySQL 的 ALTER TABLE 会隐式提交，执行前应备份并核对目标数据库。
ALTER TABLE `ai_chat` ADD CONSTRAINT `fk_ai_chat_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE `favorite` ADD CONSTRAINT `fk_favorite_news` FOREIGN KEY (`news_id`) REFERENCES `news` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE `favorite` ADD CONSTRAINT `fk_favorite_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE `history` ADD CONSTRAINT `fk_history_news` FOREIGN KEY (`news_id`) REFERENCES `news` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE `history` ADD CONSTRAINT `fk_history_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE `news` ADD CONSTRAINT `fk_news_category` FOREIGN KEY (`category_id`) REFERENCES `news_category` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE `related_news` ADD CONSTRAINT `fk_related_news_news` FOREIGN KEY (`news_id`) REFERENCES `news` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE `related_news` ADD CONSTRAINT `fk_related_news_related` FOREIGN KEY (`related_news_id`) REFERENCES `news` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE `user_token` ADD CONSTRAINT `fk_user_token_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;
