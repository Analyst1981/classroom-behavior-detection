package com.cbd.service;

import com.cbd.config.AiProperties;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RequestCallback;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.io.InputStream;
import java.util.Optional;

/**
 * 转发到 Flask AI 推理服务。
 * 所有检测能力都在 Python 侧实现，这里只做协议转发、结果解析与流代理。
 */
@Service
public class AiProxyService {

    private final RestTemplate rest;
    private final AiProperties props;
    private final ObjectMapper mapper = new ObjectMapper();

    public AiProxyService(RestTemplate aiRestTemplate, AiProperties props) {
        this.rest = aiRestTemplate;
        this.props = props;
    }

    public String baseUrl() {
        return props.getBaseUrl();
    }

    /** 转发单个文件（表单字段名由 fieldName 指定） */
    public JsonNode postFile(String path, MultipartFile file, String fieldName) {
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add(fieldName, asEntity(file, fieldName));
        return postMultipart(path, body);
    }

    /** 转发多个文件 */
    public JsonNode postFiles(String path, MultipartFile[] files, String fieldName) {
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        for (MultipartFile f : files) {
            if (f == null || f.isEmpty()) {
                continue;
            }
            body.add(fieldName, asEntity(f, fieldName));
        }
        return postMultipart(path, body);
    }

    public JsonNode postMultipart(String path, MultiValueMap<String, Object> body) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        HttpEntity<MultiValueMap<String, Object>> entity = new HttpEntity<>(body, headers);
        ResponseEntity<String> resp = rest.postForEntity(props.getBaseUrl() + path, entity, String.class);
        return toJson(resp.getBody());
    }

    public JsonNode get(String path) {
        ResponseEntity<String> resp = rest.getForEntity(props.getBaseUrl() + path, String.class);
        return toJson(resp.getBody());
    }

    public JsonNode postJson(String path, Object payload) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Object> entity = new HttpEntity<>(payload, headers);
        ResponseEntity<String> resp = rest.postForEntity(props.getBaseUrl() + path, entity, String.class);
        return toJson(resp.getBody());
    }

    public byte[] postJsonBytes(String path, Object payload) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Object> entity = new HttpEntity<>(payload, headers);
        ResponseEntity<byte[]> resp = rest.postForEntity(props.getBaseUrl() + path, entity, byte[].class);
        return resp.getBody();
    }

    /** 代理 MJPEG 实时流（视频 / 摄像头） */
    public StreamingResponseBody stream(String path) {
        return outputStream -> {
            RequestCallback callback = request -> request.getHeaders().setAccept(java.util.List.of(MediaType.ALL));
            rest.execute(props.getBaseUrl() + path, HttpMethod.GET, callback, response -> {
                try (InputStream in = response.getBody()) {
                    if (in != null) {
                        in.transferTo(outputStream);
                    }
                } catch (Exception ignore) {
                    // 客户端断开连接属于正常退出
                }
                return null;
            });
        };
    }

    public boolean healthy() {
        try {
            JsonNode node = get("/health");
            return node != null && "ok".equals(node.path("status").asText());
        } catch (Exception e) {
            return false;
        }
    }

    private HttpEntity<ByteArrayResource> asEntity(MultipartFile file, String fieldName) {
        byte[] bytes;
        try {
            bytes = file.getBytes();
        } catch (Exception e) {
            throw new IllegalArgumentException("读取上传文件失败：" + e.getMessage());
        }
        String filename = Optional.ofNullable(file.getOriginalFilename()).orElse("upload.bin");
        ByteArrayResource resource = new ByteArrayResource(bytes) {
            @Override
            public String getFilename() {
                return filename;
            }
        };
        HttpHeaders partHeaders = new HttpHeaders();
        partHeaders.setContentType(MediaType.parseMediaType(
                Optional.ofNullable(file.getContentType()).orElse(MediaType.APPLICATION_OCTET_STREAM_VALUE)));
        // 注意：不要手动设置 Content-Disposition。FormHttpMessageConverter 会依据
        // map key 生成 name，手动设置会产生重复头，导致下游解析不到该字段。
        return new HttpEntity<>(resource, partHeaders);
    }

    private JsonNode toJson(String body) {
        if (body == null || body.isBlank()) {
            return mapper.createObjectNode();
        }
        try {
            return mapper.readTree(body);
        } catch (Exception e) {
            return mapper.createObjectNode().put("raw", body);
        }
    }
}
