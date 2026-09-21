package com.cbd.service;

import com.cbd.dto.ApiResult;
import com.cbd.entity.DetectionRecord;
import com.cbd.repository.DetectionRecordRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class RecordService {

    private final DetectionRecordRepository repo;
    private final ObjectMapper mapper = new ObjectMapper();
    private static final int MAX_LABELS = 100;

    public RecordService(DetectionRecordRepository repo) {
        this.repo = repo;
    }

    /** 由 AI 服务返回结果创建单图 / 批量记录 */
    public DetectionRecord createFromImage(JsonNode res) {
        DetectionRecord r = new DetectionRecord();
        r.setTaskType("IMAGE");
        r.setSourceName(res.path("fileName").asText(""));
        r.setOutUrl(res.path("outUrl").asText(""));
        r.setCount(res.path("count").asInt(0));
        r.setElapsedMs(res.path("elapsedMs").asInt(0));
        r.setEngine(res.path("engine").asText(""));
        r.setPerClass(writeJson(res.path("stats").path("per_class")));
        JsonNode labels = res.path("labels");
        r.setLabels(writeJson(trimArray(labels)));
        return repo.save(r);
    }

    public DetectionRecord createFromBatch(JsonNode res, String sourceName) {
        DetectionRecord r = new DetectionRecord();
        r.setTaskType("BATCH");
        r.setSourceName(sourceName);
        r.setCount(res.path("totalDetections").asInt(0));
        r.setImageTotal(res.path("totalImages").asInt(0));
        r.setElapsedMs(res.path("elapsedMs").asInt(0));
        r.setEngine(res.path("engine").asText(""));
        r.setPerClass(writeJson(res.path("perClass")));
        List<JsonNode> all = new ArrayList<>();
        JsonNode results = res.path("results");
        if (results.isArray()) {
            for (JsonNode item : results) {
                all.add(item);
                if (all.size() >= MAX_LABELS) {
                    break;
                }
            }
        }
        r.setLabels(writeJson(all));
        // 取第一张作为封面图
        if (results.isArray() && results.size() > 0) {
            r.setOutUrl(results.get(0).path("outUrl").asText(""));
        }
        return repo.save(r);
    }

    public DetectionRecord createFromTask(JsonNode res, String taskType) {
        DetectionRecord r = new DetectionRecord();
        r.setTaskType(taskType);
        r.setSourceName(res.path("source").asText(""));
        r.setOutVideoUrl(res.path("outputUrl").asText(""));
        r.setEngine(res.path("engine").asText(""));
        Map<String, Integer> stats = new HashMap<>();
        JsonNode perClass = res.path("stats");
        perClass.fields().forEachRemaining(e -> stats.put(e.getKey(), e.getValue().asInt()));
        r.setPerClass(writeJson(stats));
        r.setCount(stats.values().stream().mapToInt(Integer::intValue).sum());
        return repo.save(r);
    }

    public Page<DetectionRecord> list(int page, int size, String type) {
        PageRequest pr = PageRequest.of(Math.max(0, page), Math.max(1, size), Sort.by(Sort.Direction.DESC, "createdAt"));
        if (type == null || type.isBlank()) {
            return repo.findAll(pr);
        }
        return repo.findByTaskType(type.toUpperCase(), pr);
    }

    public DetectionRecord get(Long id) {
        return repo.findById(id).orElse(null);
    }

    public void delete(Long id) {
        repo.deleteById(id);
    }

    public void deleteAll() {
        repo.deleteAll();
    }

    public DetectionRecord saveAdvice(Long id, String advice, String provider) {
        DetectionRecord r = get(id);
        if (r == null) {
            return null;
        }
        String prefix = (provider == null || provider.isBlank()) ? "" : "[" + provider + "]\n";
        r.setAdvice(prefix + advice);
        return repo.save(r);
    }

    public ApiResult stats() {
        List<Object[]> rows = repo.countGroupByType();
        List<Map<String, Object>> list = new ArrayList<>();
        int totalRecords = 0;
        int totalDetections = 0;
        for (Object[] row : rows) {
            Map<String, Object> m = new HashMap<>();
            m.put("taskType", row[0]);
            m.put("records", ((Number) row[1]).intValue());
            int detections = row[2] == null ? 0 : ((Number) row[2]).intValue();
            m.put("detections", detections);
            totalRecords += ((Number) row[1]).intValue();
            totalDetections += detections;
            list.add(m);
        }
        Map<String, Object> data = new HashMap<>();
        data.put("byType", list);
        data.put("totalRecords", totalRecords);
        data.put("totalDetections", totalDetections);
        return ApiResult.ok(data);
    }

    /** 组装 PDF 报告所需的数据（与 Flask 侧 report.py 约定一致） */
    public Map<String, Object> buildReportPayload(Long id) {
        DetectionRecord r = get(id);
        if (r == null) {
            return null;
        }
        Map<String, Object> payload = new HashMap<>();
        payload.put("id", r.getId());
        payload.put("type", r.getTaskType());
        payload.put("source", r.getSourceName());
        payload.put("createdAt", r.getCreatedAt() == null ? "" : r.getCreatedAt().toString());
        payload.put("elapsedMs", r.getElapsedMs());
        payload.put("count", r.getCount());
        payload.put("perClass", readJson(r.getPerClass()));
        payload.put("labels", readJson(r.getLabels()));
        payload.put("advice", r.getAdvice() == null ? "" : r.getAdvice());
        payload.put("engine", r.getEngine());
        return payload;
    }

    private List<JsonNode> trimArray(JsonNode arr) {
        List<JsonNode> out = new ArrayList<>();
        if (arr != null && arr.isArray()) {
            for (JsonNode n : arr) {
                out.add(n);
                if (out.size() >= MAX_LABELS) {
                    break;
                }
            }
        }
        return out;
    }

    private String writeJson(Object obj) {
        try {
            return mapper.writeValueAsString(obj);
        } catch (Exception e) {
            return "{}";
        }
    }

    private Object readJson(String s) {
        if (s == null || s.isBlank()) {
            return new HashMap<String, Object>();
        }
        try {
            return mapper.readValue(s, Object.class);
        } catch (Exception e) {
            return new HashMap<String, Object>();
        }
    }
}
