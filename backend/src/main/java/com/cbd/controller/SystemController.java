package com.cbd.controller;

import com.cbd.dto.ApiResult;
import com.cbd.service.AiProxyService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/system")
public class SystemController {

    private final AiProxyService ai;

    public SystemController(AiProxyService ai) {
        this.ai = ai;
    }

    @GetMapping("/status")
    public ApiResult status() {
        Map<String, Object> data = new HashMap<>();
        data.put("backend", "ok");
        data.put("aiServiceUrl", ai.baseUrl());
        data.put("aiServiceOnline", ai.healthy());
        try {
            data.put("model", ai.get("/api/model/status"));
        } catch (Exception e) {
            data.put("model", "unavailable");
        }
        return ApiResult.ok(data);
    }

    @GetMapping("/classes")
    public ApiResult classes() {
        try {
            return ApiResult.ok(ai.get("/api/classes"));
        } catch (Exception e) {
            return ApiResult.fail("AI 服务不可用：" + e.getMessage());
        }
    }
}
