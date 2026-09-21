package com.cbd.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestTemplate;

import java.net.HttpURLConnection;

@Configuration
public class RestTemplateConfig {

    @Bean
    public RestTemplate aiRestTemplate(AiProperties props) {
        // 说明：不要在此处调用 connection.setChunkedStreamingMode(0)。
        // 该设置会隐式把 doOutput 置为 true，导致后续 GET 请求抛出
        // "cannot write to a URLConnection if doOutput=false"。
        // MJPEG 代理是「响应流」场景（GET），无需开启请求分块。
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(props.getConnectTimeoutMs());
        factory.setReadTimeout(props.getReadTimeoutMs());
        return new RestTemplate(factory);
    }
}
