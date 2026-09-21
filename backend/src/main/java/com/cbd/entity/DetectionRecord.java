package com.cbd.entity;

import jakarta.persistence.*;

import java.time.LocalDateTime;

/** 检测记录：单图 / 批量 / 视频 / 摄像头四类共用一张表。 */
@Entity
@Table(name = "detection_record", indexes = {
        @Index(name = "idx_record_created", columnList = "created_at"),
        @Index(name = "idx_record_type", columnList = "task_type")
})
public class DetectionRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** IMAGE / BATCH / VIDEO / CAMERA */
    @Column(name = "task_type", length = 16)
    private String taskType;

    /** 来源文件名（摄像头为 camera:index） */
    @Column(name = "source_name", length = 255)
    private String sourceName;

    /** 结果图访问地址（AI 服务静态目录） */
    @Column(name = "out_url", length = 512)
    private String outUrl;

    /** 结果视频地址 */
    @Column(name = "out_video_url", length = 512)
    private String outVideoUrl;

    /** 检出目标数 */
    @Column(name = "detect_count")
    private Integer count = 0;

    /** 推理耗时（毫秒） */
    @Column(name = "elapsed_ms")
    private Integer elapsedMs = 0;

    /** 各类别统计 JSON，如 {"抬头听课":12,"举手":3} */
    @Column(name = "per_class", columnDefinition = "TEXT")
    private String perClass;

    /** 检测明细 JSON（最多保存 100 条） */
    @Column(name = "labels", columnDefinition = "LONGTEXT")
    private String labels;

    /** AI 生成的分析建议 */
    @Column(name = "advice", columnDefinition = "LONGTEXT")
    private String advice;

    /** 运行引擎：ultralytics / demo */
    @Column(name = "engine", length = 32)
    private String engine;

    /** 批量检测时的图片数量 */
    @Column(name = "image_total")
    private Integer imageTotal = 0;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    public void prePersist() {
        if (createdAt == null) {
            createdAt = LocalDateTime.now();
        }
        if (count == null) {
            count = 0;
        }
        if (elapsedMs == null) {
            elapsedMs = 0;
        }
        if (imageTotal == null) {
            imageTotal = 0;
        }
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getTaskType() {
        return taskType;
    }

    public void setTaskType(String taskType) {
        this.taskType = taskType;
    }

    public String getSourceName() {
        return sourceName;
    }

    public void setSourceName(String sourceName) {
        this.sourceName = sourceName;
    }

    public String getOutUrl() {
        return outUrl;
    }

    public void setOutUrl(String outUrl) {
        this.outUrl = outUrl;
    }

    public String getOutVideoUrl() {
        return outVideoUrl;
    }

    public void setOutVideoUrl(String outVideoUrl) {
        this.outVideoUrl = outVideoUrl;
    }

    public Integer getCount() {
        return count;
    }

    public void setCount(Integer count) {
        this.count = count;
    }

    public Integer getElapsedMs() {
        return elapsedMs;
    }

    public void setElapsedMs(Integer elapsedMs) {
        this.elapsedMs = elapsedMs;
    }

    public String getPerClass() {
        return perClass;
    }

    public void setPerClass(String perClass) {
        this.perClass = perClass;
    }

    public String getLabels() {
        return labels;
    }

    public void setLabels(String labels) {
        this.labels = labels;
    }

    public String getAdvice() {
        return advice;
    }

    public void setAdvice(String advice) {
        this.advice = advice;
    }

    public String getEngine() {
        return engine;
    }

    public void setEngine(String engine) {
        this.engine = engine;
    }

    public Integer getImageTotal() {
        return imageTotal;
    }

    public void setImageTotal(Integer imageTotal) {
        this.imageTotal = imageTotal;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }
}
