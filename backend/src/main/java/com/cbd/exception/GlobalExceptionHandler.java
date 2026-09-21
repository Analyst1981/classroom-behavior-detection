package com.cbd.exception;

import com.cbd.dto.ApiResult;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

    /** AI 服务不可达等运行期异常 */
    @ExceptionHandler(Exception.class)
    public ApiResult handle(Exception e) {
        String msg = e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage();
        if (msg.contains("Connection refused") || msg.contains("connect")) {
            return ApiResult.fail(503, "AI 推理服务未启动或不可达，请先启动 ai-service（默认 5000 端口）：" + msg);
        }
        return ApiResult.fail(msg);
    }
}
