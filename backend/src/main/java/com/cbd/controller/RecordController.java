package com.cbd.controller;

import com.cbd.entity.DetectionRecord;
import com.cbd.service.AiProxyService;
import com.cbd.service.RecordService;
import com.cbd.dto.ApiResult;
import org.springframework.core.io.InputStreamResource;
import org.springframework.data.domain.Page;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.ByteArrayInputStream;
import java.util.Map;

/** 检测记录管理 + PDF 报告导出 */
@RestController
@RequestMapping("/api/records")
public class RecordController {

    private final RecordService records;
    private final AiProxyService ai;

    public RecordController(RecordService records, AiProxyService ai) {
        this.records = records;
        this.ai = ai;
    }

    @GetMapping
    public ApiResult list(@RequestParam(defaultValue = "0") int page,
                          @RequestParam(defaultValue = "10") int size,
                          @RequestParam(required = false) String type) {
        Page<DetectionRecord> p = records.list(page, size, type);
        Map<String, Object> data = new java.util.HashMap<>();
        data.put("content", p.getContent());
        data.put("total", p.getTotalElements());
        data.put("page", p.getNumber());
        data.put("size", p.getSize());
        return ApiResult.ok(data);
    }

    @GetMapping("/{id}")
    public ApiResult get(@PathVariable Long id) {
        DetectionRecord r = records.get(id);
        return r == null ? ApiResult.fail(404, "记录不存在") : ApiResult.ok(r);
    }

    @DeleteMapping("/{id}")
    public ApiResult delete(@PathVariable Long id) {
        records.delete(id);
        return ApiResult.ok();
    }

    @DeleteMapping
    public ApiResult clear() {
        records.deleteAll();
        return ApiResult.ok();
    }

    /** 为某条记录生成并保存 AI 建议 */
    @PostMapping("/{id}/advice")
    public ApiResult advice(@PathVariable Long id, @RequestBody(required = false) Map<String, Object> body) {
        DetectionRecord r = records.get(id);
        if (r == null) {
            return ApiResult.fail(404, "记录不存在");
        }
        Map<String, Object> payload = new java.util.HashMap<>();
        payload.put("stats", parseStats(r));
        payload.put("provider", body == null ? null : body.get("provider"));
        com.fasterxml.jackson.databind.JsonNode res = ai.postJson("/api/ai/advice", payload);
        String content = res.path("content").asText("");
        String provider = res.path("provider").asText("");
        DetectionRecord saved = records.saveAdvice(id, content, provider);
        Map<String, Object> data = new java.util.HashMap<>();
        data.put("advice", content);
        data.put("provider", provider);
        data.put("fallback", res.path("fallback").asBoolean(false));
        data.put("recordId", saved == null ? null : saved.getId());
        return ApiResult.ok(data);
    }

    /** 导出 PDF 报告 */
    @GetMapping("/{id}/report")
    public ResponseEntity<InputStreamResource> report(@PathVariable Long id) {
        Map<String, Object> payload = records.buildReportPayload(id);
        if (payload == null) {
            return ResponseEntity.notFound().build();
        }
        byte[] pdf = ai.postJsonBytes("/api/report/pdf", payload);
        if (pdf == null) {
            return ResponseEntity.internalServerError().build();
        }
        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_PDF)
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\"classroom-report-" + id + ".pdf\"")
                .body(new InputStreamResource(new ByteArrayInputStream(pdf)));
    }

    @GetMapping("/stats")
    public ApiResult stats() {
        return records.stats();
    }

    private Map<String, Object> parseStats(DetectionRecord r) {
        Map<String, Object> stats = new java.util.HashMap<>();
        stats.put("total", r.getCount() == null ? 0 : r.getCount());
        Map<String, Object> perClass = new java.util.HashMap<>();
        String json = r.getPerClass();
        if (json != null && !json.isBlank()) {
            try {
                com.fasterxml.jackson.databind.ObjectMapper m = new com.fasterxml.jackson.databind.ObjectMapper();
                perClass = m.readValue(json, Map.class);
            } catch (Exception ignored) {
                perClass = new java.util.HashMap<>();
            }
        }
        stats.put("per_class", perClass);
        stats.put("task_type", r.getTaskType());
        stats.put("source", r.getSourceName());
        return stats;
    }
}
