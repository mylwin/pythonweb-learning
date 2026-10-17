-- 已有 tb_book 表执行本迁移一次；新建表由 Book 模型自动包含 price 字段。
-- create_all() 不会给已有表添加字段。
-- 已有记录的 price 初始化为 0.00，后续可按实际价格修改。
USE `python_web_study`;

ALTER TABLE `tb_book`
ADD COLUMN `price` DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT '图书价格（元）'
AFTER `author`;
