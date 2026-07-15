# Training Qualification Policy

中文业务口径：

培训达标率用于衡量客户成功人员到学校完成产品培训后的效果。默认达标条件为培训后目标用户使用率达到 40% 及以上。

为了兼容不同 AI 教育产品的目标用户差异，系统将教师使用率和学生使用率按产品权重计算为综合培训效果分：

```text
培训效果分 = 教师使用率 * 教师权重 + 学生使用率 * 学生权重
是否达标 = 培训效果分 >= 40%
培训达标率 = 达标培训项目数 / 培训项目总数
```

Training qualification is judged by post-training product usage.

Default rule:

- training_effect_score = teacher_usage_rate * teacher_weight + student_usage_rate * student_weight
- is_qualified = training_effect_score >= 0.4

Product weights:

- 星未来: teacher 0.7, student 0.3
- 星乐读: teacher 0.3, student 0.7
- 星学伴: teacher 0.5, student 0.5
- 鸿儒教研: teacher 0.8, student 0.2
- 海班慧: teacher 0.6, student 0.4

This design keeps the business rule configurable, because different education products target different user groups.
