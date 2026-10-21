-- 智能停车场车牌识别系统 - 数据库初始化脚本
-- 创建数据库
CREATE DATABASE IF NOT EXISTS smart_parking CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_parking;

-- 用户表（管理员/操作员）
CREATE TABLE IF NOT EXISTS `users` (
  `id`         INT          NOT NULL AUTO_INCREMENT,
  `username`   VARCHAR(50)  NOT NULL UNIQUE COMMENT '用户名',
  `password`   VARCHAR(255) NOT NULL COMMENT '密码(bcrypt hash)',
  `real_name`  VARCHAR(50)           COMMENT '真实姓名',
  `role`       ENUM('admin','operator') NOT NULL DEFAULT 'operator' COMMENT '角色',
  `status`     TINYINT      NOT NULL DEFAULT 1 COMMENT '状态 1启用 0禁用',
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 停车记录表
CREATE TABLE IF NOT EXISTS `parking_records` (
  `id`           BIGINT       NOT NULL AUTO_INCREMENT,
  `plate_number` VARCHAR(20)  NOT NULL COMMENT '车牌号码',
  `plate_type`   VARCHAR(20)           COMMENT '车牌类型: blue/yellow/green',
  `entry_time`   DATETIME     NOT NULL COMMENT '入场时间',
  `exit_time`    DATETIME               COMMENT '离场时间',
  `duration`     INT                    COMMENT '停车时长(分钟)',
  `fee`          DECIMAL(10,2)          COMMENT '停车费用(元)',
  `status`       ENUM('parked','exited','exception') NOT NULL DEFAULT 'parked' COMMENT '状态',
  `payment_status` VARCHAR(10) NOT NULL DEFAULT 'unpaid' COMMENT '支付状态: unpaid待支付/paid已支付/free免费放行',
  `payment_time`   DATETIME             COMMENT '支付时间',
  `entry_image`  VARCHAR(255)           COMMENT '入场图片路径',
  `exit_image`   VARCHAR(255)           COMMENT '离场图片路径',
  `operator_id`  INT                    COMMENT '操作员ID',
  `remark`       VARCHAR(255)           COMMENT '备注',
  `created_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_plate` (`plate_number`),
  KEY `idx_entry_time` (`entry_time`),
  KEY `idx_status` (`status`),
  KEY `idx_payment_status` (`payment_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='停车记录表';

-- 计费规则表
CREATE TABLE IF NOT EXISTS `fee_rules` (
  `id`           INT          NOT NULL AUTO_INCREMENT,
  `rule_name`    VARCHAR(100) NOT NULL COMMENT '规则名称',
  `vehicle_type` VARCHAR(20)  NOT NULL DEFAULT 'all' COMMENT '车辆类型: all/car/truck',
  `fee_type`     ENUM('hourly','flat') NOT NULL DEFAULT 'hourly' COMMENT '计费方式: hourly按小时, flat按次',
  `free_minutes` INT          NOT NULL DEFAULT 15 COMMENT '免费停车分钟数',
  `price_per_hour` DECIMAL(10,2) COMMENT '每小时费用(hourly模式)',
  `flat_price`   DECIMAL(10,2) COMMENT '按次收费金额(flat模式)',
  `max_daily`    DECIMAL(10,2) COMMENT '单日封顶金额',
  `time_start`   TIME                  COMMENT '生效开始时间(NULL=全天)',
  `time_end`     TIME                  COMMENT '生效结束时间',
  `is_active`    TINYINT      NOT NULL DEFAULT 1 COMMENT '是否启用',
  `created_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='计费规则表';

-- 车位信息表
CREATE TABLE IF NOT EXISTS `parking_spaces` (
  `id`           INT          NOT NULL AUTO_INCREMENT,
  `total`        INT          NOT NULL DEFAULT 100 COMMENT '总车位数',
  `available`    INT          NOT NULL DEFAULT 100 COMMENT '可用车位数',
  `updated_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='车位统计表';

-- V2 新增：月租车辆表
CREATE TABLE IF NOT EXISTS `monthly_subscribers` (
  `id`           INT          NOT NULL AUTO_INCREMENT,
  `plate_number` VARCHAR(20)  NOT NULL UNIQUE COMMENT '车牌号',
  `owner_name`   VARCHAR(50)  NOT NULL COMMENT '车主姓名',
  `phone`        VARCHAR(20)           COMMENT '联系电话',
  `package_name` VARCHAR(100) NOT NULL COMMENT '套餐名称',
  `start_date`   DATE         NOT NULL COMMENT '生效日期',
  `end_date`     DATE         NOT NULL COMMENT '到期日期',
  `fee`          DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '套餐费用(元)',
  `remark`       VARCHAR(255)          COMMENT '备注',
  `created_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_monthly_plate` (`plate_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='月租车辆表';

-- V2 新增：车位预约表
CREATE TABLE IF NOT EXISTS `parking_reservations` (
  `id`           INT          NOT NULL AUTO_INCREMENT,
  `plate_number` VARCHAR(20)  NOT NULL COMMENT '车牌号',
  `owner_name`   VARCHAR(50)           COMMENT '预约人姓名',
  `phone`        VARCHAR(20)           COMMENT '联系电话',
  `start_time`   DATETIME     NOT NULL COMMENT '预约开始时间',
  `end_time`     DATETIME     NOT NULL COMMENT '预约结束时间',
  `status`       ENUM('pending','arrived','cancelled','expired') NOT NULL DEFAULT 'pending' COMMENT '状态',
  `remark`       VARCHAR(255)          COMMENT '备注',
  `created_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_reservation_plate` (`plate_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='车位预约表';

-- V2 新增：黑名单表
CREATE TABLE IF NOT EXISTS `blacklist` (
  `id`           INT          NOT NULL AUTO_INCREMENT,
  `plate_number` VARCHAR(20)  NOT NULL UNIQUE COMMENT '车牌号',
  `reason`       VARCHAR(255)          COMMENT '拉黑原因',
  `debt_amount`  DECIMAL(10,2) DEFAULT 0 COMMENT '欠费金额(元)',
  `is_active`    TINYINT      NOT NULL DEFAULT 1 COMMENT '是否启用拦截 1启用 0解除',
  `created_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_blacklist_plate` (`plate_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='黑名单表';

-- V2 新增：操作日志表
CREATE TABLE IF NOT EXISTS `operation_logs` (
  `id`         BIGINT       NOT NULL AUTO_INCREMENT,
  `user_id`    INT                   COMMENT '操作用户ID',
  `username`   VARCHAR(50)           COMMENT '操作用户名',
  `action`     VARCHAR(50)  NOT NULL COMMENT '操作类型: login/enter/exit/create/update/delete/export/block',
  `target`     VARCHAR(100)          COMMENT '操作对象',
  `detail`     VARCHAR(255)          COMMENT '操作详情',
  `ip`         VARCHAR(50)           COMMENT '客户端IP',
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_log_action` (`action`),
  KEY `idx_log_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作日志表';

-- 初始数据
-- 默认管理员账号: admin / admin123
INSERT INTO `users` (`username`, `password`, `real_name`, `role`) VALUES
('admin', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36QeJsVX/6nJqNwJEt4s.Nm', '系统管理员', 'admin'),
('operator1', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36QeJsVX/6nJqNwJEt4s.Nm', '操作员张三', 'operator');

-- 默认计费规则
INSERT INTO `fee_rules` (`rule_name`, `vehicle_type`, `fee_type`, `free_minutes`, `price_per_hour`, `max_daily`, `is_active`) VALUES
('普通小时计费', 'all', 'hourly', 15, 5.00, 50.00, 1);

-- 初始车位
INSERT INTO `parking_spaces` (`total`, `available`) VALUES (100, 100);

-- V2 初始数据：月租车辆演示数据
INSERT INTO `monthly_subscribers` (`plate_number`, `owner_name`, `phone`, `package_name`, `start_date`, `end_date`, `fee`, `remark`) VALUES
('皖A88888', '张先生', '13800000001', '标准月租套餐', DATE_SUB(CURDATE(), INTERVAL 20 DAY), DATE_ADD(CURDATE(), INTERVAL 40 DAY), 300.00, '演示数据：月租车'),
('皖B66666', '李女士', '13800000002', '季度优惠套餐', DATE_SUB(CURDATE(), INTERVAL 90 DAY), DATE_ADD(CURDATE(), INTERVAL 5 DAY), 800.00, '演示数据：即将到期');

-- V2 初始数据：车位预约演示数据
INSERT INTO `parking_reservations` (`plate_number`, `owner_name`, `phone`, `start_time`, `end_time`, `status`, `remark`) VALUES
('皖C12345', '王先生', '13800000003', DATE_ADD(NOW(), INTERVAL 1 HOUR), DATE_ADD(NOW(), INTERVAL 3 HOUR), 'pending', '演示数据：预约2小时后入场'),
('皖D56789', '赵女士', '13800000004', DATE_SUB(NOW(), INTERVAL 30 MINUTE), DATE_ADD(NOW(), INTERVAL 2 HOUR), 'pending', '演示数据：预约时段内');
