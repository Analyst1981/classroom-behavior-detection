package com.cbd.repository;

import com.cbd.entity.DetectionRecord;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface DetectionRecordRepository extends JpaRepository<DetectionRecord, Long> {

    Page<DetectionRecord> findByTaskType(String taskType, Pageable pageable);

    @Query("select r.taskType as taskType, count(r) as cnt, sum(r.count) as total "
            + "from DetectionRecord r group by r.taskType")
    List<Object[]> countGroupByType();

    @Modifying
    @Query("delete from DetectionRecord r where r.taskType = :type")
    int deleteByType(@Param("type") String type);
}
