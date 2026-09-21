package com.cbd.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/** AI 推理服务（Flask）连接配置，对应 application.yml 的 ai.* */
@Component
@ConfigurationProperties(prefix = "ai")
public class AiProperties {

    /** Flask 服务地址，如 http://127.0.0.1:5000 */
    private String baseUrl = "http://127.0.0.1:5000";
    private int connectTimeoutMs = 20000;
    private int readTimeoutMs = 120000;
    private String staticPrefix = "/static/outputs";

    public String getBaseUrl() {
        return baseUrl;
    }

    public void setBaseUrl(String baseUrl) {
        this.baseUrl = baseUrl;
    }

    public int getConnectTimeoutMs() {
        return connectTimeoutMs;
    }

    public void setConnectTimeoutMs(int connectTimeoutMs) {
        this.connectTimeoutMs = connectTimeoutMs;
    }

    public int getReadTimeoutMs() {
        return readTimeoutMs;
    }

    public void setReadTimeoutMs(int readTimeoutMs) {
        this.readTimeoutMs = readTimeoutMs;
    }

    public String getStaticPrefix() {
        return staticPrefix;
    }

    public void setStaticPrefix(String staticPrefix) {
        this.staticPrefix = staticPrefix;
    }
}
