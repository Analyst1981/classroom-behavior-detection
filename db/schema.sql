-- =============================================================
-- 课堂行为智能检测系统 —— MySQL 数据库脚本
-- 说明：后端使用 JPA ddl-auto=update，启动后会自动建表；
--       本脚本用于「手工建库建表」或需要在生产环境固定表结构时使用。
-- =============================================================

CREATE DATABASE IF NOT EXISTS classroom_behavior
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_general_ci;

USE classroom_behavior;

DROP TABLE IF EXISTS detection_record;

CREATE TABLE detection_record (
    id            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    task_type     VARCHAR(16)  DEFAULT NULL COMMENT 'IMAGE/BATCH/VIDEO/CAMERA',
    source_name   VARCHAR(255) DEFAULT NULL COMMENT '来源文件名',
    out_url       VARCHAR(512) DEFAULT NULL COMMENT '结果图地址',
    out_video_url VARCHAR(512) DEFAULT NULL COMMENT '结果视频地址',
    detect_count  INT          DEFAULT 0 COMMENT '检出目标数',
    elapsed_ms    INT          DEFAULT 0 COMMENT '推理耗时(ms)',
    per_class     TEXT         COMMENT '类别统计 JSON',
    labels        LONGTEXT     COMMENT '检测明细 JSON',
    advice        LONGTEXT     COMMENT 'AI 分析建议',
    engine        VARCHAR(32)  DEFAULT NULL COMMENT '推理引擎 ultralytics/demo',
    image_total   INT          DEFAULT 0 COMMENT '批量检测图片数',
    created_at    DATETIME     DEFAULT NULL COMMENT '创建时间',
    PRIMARY KEY (id),
    KEY idx_record_created (created_at),
    KEY idx_record_type (task_type)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COMMENT = '课堂行为检测记录表';

-- 初始化校验数据（可按需删除）
-- INSERT INTO detection_record (task_type, source_name, detect_count, created_at)
-- VALUES ('IMAGE', 'sample.jpg', 0, NOW());
