-- 词根校验表
DROP TABLE IF EXISTS root_word_check;
CREATE TABLE root_word_check (
    root_word_id BIGINT NOT NULL PRIMARY KEY,
    platform_code VARCHAR(200),
    platform_name VARCHAR(500),
    main_category_code VARCHAR(200),
    main_category_name VARCHAR(500),
    site_code VARCHAR(200),
    site_name VARCHAR(500),
    website VARCHAR(500),
    root_word VARCHAR(500),
    keywords TEXT,
    uptime TIMESTAMP DEFAULT now()
);

-- 表注释
COMMENT ON TABLE root_word_check IS '词根校验表（来源ERP视图root_word_check_v）';

-- 字段注释
COMMENT ON COLUMN root_word_check.root_word_id IS '词根ID';
COMMENT ON COLUMN root_word_check.platform_code IS '平台编码';
COMMENT ON COLUMN root_word_check.platform_name IS '平台名称';
COMMENT ON COLUMN root_word_check.main_category_code IS '主营类目编码';
COMMENT ON COLUMN root_word_check.main_category_name IS '主营类目名称';
COMMENT ON COLUMN root_word_check.site_code IS '站点编码';
COMMENT ON COLUMN root_word_check.site_name IS '站点名称';
COMMENT ON COLUMN root_word_check.website IS '站点网址';
COMMENT ON COLUMN root_word_check.root_word IS '词根';
COMMENT ON COLUMN root_word_check.keywords IS '关键词';
COMMENT ON COLUMN root_word_check.uptime IS '更新时间';


DROP TABLE IF EXISTS root_word_check_log;
CREATE TABLE root_word_check_log
(
    id             BIGSERIAL PRIMARY KEY,
    root_word_id   BIGINT                  not null,
    website        varchar(500)            not null,
    root_word      VARCHAR(500)            not null,
    keywords       text                    not null,
    root_word_type VARCHAR(10)             not null,
    check_remark   VARCHAR(1024)           not null,
    erp_api_status VARCHAR(10) default '0' not null,
    erp_api_msg    VARCHAR(1024),
    uptime         TIMESTAMP   DEFAULT NOW()
);

-- 字段注释
COMMENT ON COLUMN root_word_check_log.id IS '自增ID';
COMMENT ON COLUMN root_word_check_log.root_word_id IS '词根ID';
COMMENT ON COLUMN root_word_check_log.website IS '站点网站';
COMMENT ON COLUMN root_word_check_log.root_word IS '词根';
COMMENT ON COLUMN root_word_check_log.keywords IS '关键词';
COMMENT ON COLUMN root_word_check_log.root_word_type IS '词根类型（0有效词根 1无效词根）';
COMMENT ON COLUMN root_word_check_log.check_remark IS '校验备注';
COMMENT ON COLUMN root_word_check_log.erp_api_status IS 'ERP API状态（0待请求 1请求成功 2请求失败）';
COMMENT ON COLUMN root_word_check_log.erp_api_msg IS 'ERP API备注';
COMMENT ON COLUMN root_word_check_log.uptime IS '更新时间';

-- 表注释
COMMENT ON TABLE root_word_check_log IS '词根校验日志表';


DROP TABLE IF EXISTS root_word_check_title;
CREATE TABLE root_word_check_title
(
    id              BIGSERIAL PRIMARY KEY,
    root_word_id    BIGINT        not null,
    title           TEXT          not null,
    product_url     TEXT,
    keyword_matched VARCHAR(500),
    uptime          TIMESTAMP DEFAULT NOW()
);

-- 字段注释
COMMENT ON COLUMN root_word_check_title.id IS '自增ID';
COMMENT ON COLUMN root_word_check_title.root_word_id IS '词根ID';
COMMENT ON COLUMN root_word_check_title.title IS '搜索标题';
COMMENT ON COLUMN root_word_check_title.product_url IS '商品链接';
COMMENT ON COLUMN root_word_check_title.keyword_matched IS '命中的关键词';
COMMENT ON COLUMN root_word_check_title.uptime IS '更新时间';

-- 表注释
COMMENT ON TABLE root_word_check_title IS '词根校验标题表（抓取的搜索标题）';