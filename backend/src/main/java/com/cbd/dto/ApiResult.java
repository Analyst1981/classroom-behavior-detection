package com.cbd.dto;

import java.util.HashMap;
import java.util.Map;

/** 统一响应结构：{code, message, data} */
public class ApiResult {

    private int code;
    private String message;
    private Object data;

    public ApiResult() {
    }

    public ApiResult(int code, String message, Object data) {
        this.code = code;
        this.message = message;
        this.data = data;
    }

    public static ApiResult ok(Object data) {
        return new ApiResult(0, "success", data);
    }

    public static ApiResult ok() {
        return new ApiResult(0, "success", null);
    }

    public static ApiResult fail(String message) {
        return new ApiResult(500, message, null);
    }

    public static ApiResult fail(int code, String message) {
        return new ApiResult(code, message, null);
    }

    public static Map<String, Object> map() {
        return new HashMap<>();
    }

    public int getCode() {
        return code;
    }

    public void setCode(int code) {
        this.code = code;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public Object getData() {
        return data;
    }

    public void setData(Object data) {
        this.data = data;
    }
}
