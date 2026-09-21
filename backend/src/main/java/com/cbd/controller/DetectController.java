package com.cbd.controller;

import com.cbd.dto.ApiResult;
import com.cbd.service.AiProxyService;
import com.cbd.service.RecordService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.util.HashMap;
import java.util.Map;

/** 检测相关接口：全部转发 AI 服务，并在本地落库形成检测记录。 */
@RestController
@RequestMapping("/api")
public class DetectController {

    private final AiProxyService ai;
    private final RecordService records;
    private final ObjectMapper mapper = new ObjectMapper();

    public DetectController(AiProxyService ai, RecordService records) {
        this.ai = ai;
        this.records = records;
    }

    /** 单张图片检测 */
    @PostMapping(value = "/detect/image", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ApiResult detectImage(@RequestParam("file") MultipartFile file) {
        JsonNode res = ai.postFile("/api/detect/image", file, "file");
        if (!res.path("ok").asBoolean(false)) {
            return ApiResult.fail(res.path("error").asText("AI 服务返回失败"));
        }
        return ApiResult.ok(withRecordId(res, records.createFromImage(res).getId()));
    }

    /** 图片文件夹批量检测：支持多文件，或直接上传前端用 JSZip 打好的 zip */
    @PostMapping(value = "/detect/batch", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ApiResult detectBatch(@RequestParam(value = "files", required = false) MultipartFile[] files,
                                 @RequestParam(value = "zip", required = false) MultipartFile zip) {
        JsonNode res;
        String sourceName;
        if (zip != null && !zip.isEmpty()) {
            res = ai.postFile("/api/detect/batch", zip, "zip");
            sourceName = zip.getOriginalFilename();
        } else {
            res = ai.postFiles("/api/detect/batch", files == null ? new MultipartFile[0] : files, "files");
            sourceName = (files != null && files.length > 0) ? (files.length + " 张图片") : "";
        }
        if (!res.path("ok").asBoolean(false)) {
            return ApiResult.fail(res.path("error").asText("AI 服务返回失败"));
        }
        return ApiResult.ok(withRecordId(res, records.createFromBatch(res, sourceName).getId()));
    }

    /** 上传视频：创建异步任务，返回 taskId */
    @PostMapping(value = "/detect/video", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ApiResult detectVideo(@RequestParam("file") MultipartFile file) {
        JsonNode res = ai.postFile("/api/detect/video", file, "file");
        if (!res.path("ok").asBoolean(false)) {
            return ApiResult.fail(res.path("error").asText("AI 服务返回失败"));
        }
        return ApiResult.ok(res);
    }

    /** 查询视频/摄像头任务状态 */
    @GetMapping("/detect/task/{taskId}")
    public ApiResult taskStatus(@PathVariable String taskId) {
        return ApiResult.ok(ai.get("/api/task/" + taskId));
    }

    /** 视频任务完成后保存为记录 */
    @PostMapping("/detect/video/{taskId}/save")
    public ApiResult saveVideoRecord(@PathVariable String taskId) {
        JsonNode res = ai.get("/api/task/" + taskId);
        String status = res.path("status").asText("");
        if (!res.path("ok").asBoolean(false) || "error".equals(status) || status.isBlank()) {
            return ApiResult.fail("任务未完成或不存在（status=" + status + "）");
        }
        return ApiResult.ok(withRecordId(res, records.createFromTask(res, "VIDEO").getId()));
    }

    /** 视频实时流（MJPEG）代理 */
    @GetMapping("/detect/stream/video/{taskId}")
    public ResponseEntity<StreamingResponseBody> videoStream(@PathVariable String taskId) {
        return ResponseEntity.ok()
                .contentType(MediaType.valueOf("multipart/x-mixed-replace; boundary=frame"))
                .body(ai.stream("/api/video/stream/" + taskId));
    }

    /** 打开摄像头 */
    @PostMapping("/camera/start")
    public ApiResult cameraStart(@RequestBody(required = false) Map<String, Object> body) {
        Map<String, Object> payload = body == null ? new HashMap<>() : body;
        payload.putIfAbsent("index", 0);
        payload.putIfAbsent("record", false);
        return ApiResult.ok(ai.postJson("/api/camera/start", payload));
    }

    /** 关闭摄像头 */
    @PostMapping("/camera/stop/{taskId}")
    public ApiResult cameraStop(@PathVariable String taskId) {
        return ApiResult.ok(ai.postJson("/api/camera/stop/" + taskId, new HashMap<String, Object>()));
    }

    /** 保存摄像头检测记录 */
    @PostMapping("/camera/{taskId}/save")
    public ApiResult saveCameraRecord(@PathVariable String taskId) {
        JsonNode res = ai.get("/api/task/" + taskId);
        return ApiResult.ok(withRecordId(res, records.createFromTask(res, "CAMERA").getId()));
    }

    /** 摄像头实时流（MJPEG）代理 */
    @GetMapping("/detect/stream/camera/{taskId}")
    public ResponseEntity<StreamingResponseBody> cameraStream(@PathVariable String taskId) {
        return ResponseEntity.ok()
                .contentType(MediaType.valueOf("multipart/x-mixed-replace; boundary=frame"))
                .body(ai.stream("/api/camera/stream/" + taskId));
    }

    /** AI 教学建议（DeepSeek / Qwen） */
    @PostMapping("/ai/advice")
    public ApiResult advice(@RequestBody Map<String, Object> body) {
        JsonNode res = ai.postJson("/api/ai/advice", body);
        return ApiResult.ok(res);
    }

    /** AI 服务与模型状态 */
    @GetMapping("/ai/status")
    public ApiResult aiStatus() {
        return ApiResult.ok(ai.get("/api/model/status"));
    }

    private JsonNode withRecordId(JsonNode res, Long recordId) {
        if (res instanceof ObjectNode) {
            ((ObjectNode) res).put("recordId", recordId);
            return res;
        }
        ObjectNode node = mapper.createObjectNode();
        node.set("result", res);
        node.put("recordId", recordId);
        return node;
    }
}
