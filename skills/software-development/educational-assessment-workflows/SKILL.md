---
name: educational-assessment-workflows
description: "Batch grading and assessment workflows for educational assignments with structured feedback and progress tracking."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [education, grading, assessment, feedback, batch-processing]
    related_skills: [github-code-review, writing-plans]
---

# Educational Assessment Workflows

Batch grading and assessment workflows for educational assignments with structured feedback and progress tracking. This skill covers systematic approaches to reviewing student work, providing consistent feedback, and maintaining progress across multiple assignments.

## When to Use

- Batch grading student assignments
- Providing structured feedback on programming assignments
- Tracking grading progress across multiple students
- Creating reusable grading templates and standards
- Generating reports for teachers/educators

## Core Principles

### 1. Structured Output Organization
**User preference discovered from session:** When grading assignments, save results to desktop folders organized by subject/chapter for future reference and easy navigation.

**Standard folder structure:**
```
Desktop/作业批改/
├── [Subject]/               # e.g., SpringCloud
│   ├── [Chapter]/           # e.g., T8
│   │   ├── 批改报告_[date].md
│   │   ├── 评分表_[date].csv
│   │   ├── 批改进度跟踪.md
│   │   └── 批改中期报告_[date].md
│   └── 批改说明.md
└── [OtherSubject]/
```

### 2. Multi-Format Documentation
Create multiple complementary documents for different use cases:

- **Markdown reports** for detailed feedback and analysis
- **CSV spreadsheets** for easy data manipulation and statistics
- **Progress tracking** files for ongoing work management
- **Summary reports** for quick overviews

### 3. Consistent Grading Standards
Establish and maintain consistent scoring criteria:

**Standard scoring dimensions (5-point system):**
1. **项目结构 (20分)** - Project organization and structure
2. **功能实现 (30分)** - Feature implementation completeness
3. **代码规范 (25分)** - Code quality and standards
4. **配置正确性 (15分)** - Configuration correctness
5. **扩展性 (10分)** - Extensibility and advanced features

**Grading scale:**
- 90-100: 优秀 (Excellent)
- 80-89: 良好 (Good)
- 70-79: 中等 (Average)
- 60-69: 及格 (Passing)
- 0-59: 不及格 (Failing)

## Workflow: Batch Grading Student Assignments

### Step 1: Initial Setup and Exploration

```bash
# Explore assignment folder structure
find "D:\六职\作业收集\2401\springcloud" -type f -name "*.java" -o -name "*.yml" -o -name "*.yaml" | head -10

# Identify latest/modified chapters
ls -la "D:\六职\作业收集\2401\springcloud" | grep -E "^d" | tail -5

# Create grading output structure
mkdir -p "$HOME/Desktop/作业批改/SpringCloud/T8"
```

### Step 2: Sample Assessment (First 3-4 Students)

**Purpose:** Establish grading standards and identify common patterns before full batch grading.

1. **Select representative samples:**
   - 2-3 students with complete submissions
   - 1 student with partial/incomplete work
   - Aim for diverse skill levels

2. **Key files to examine for each student:**
   - Main application/controller files
   - Configuration files (application.yml)
   - Service/interface definitions
   - Project structure files (pom.xml, build.gradle)

3. **Common patterns to identify:**
   - Recurring syntax errors
   - Configuration mistakes
   - Missing features or components
   - Best practices violations

### Step 3: Create Grading Templates

**Scoring spreadsheet template (CSV):**
```csv
学生姓名,学号,项目结构(20),功能实现(30),代码规范(25),配置正确性(15),扩展性(10),总分(100),等级,评语
[姓名],[学号],,,,,,,待批改,
```

**Progress tracking template:**
```markdown
# [Subject] [Chapter] 作业批改进度跟踪

## 基本信息
- **作业文件夹**: [path]
- **总学生数**: [number]
- **批改开始日期**: [date]
- **批改教师**: [name]

## 批改进度

### ✅ 已完成批改 ([X]人)
[student list with scores]

### ⏳ 待批改 ([Y]人)
[student list]

## 批改记录
| 日期 | 批改学生数 | 累计完成 | 备注 |
|------|------------|----------|------|
[progress records]
```

### Step 4: Systematic Batch Grading

**For each student:**

1. **Quick scan for completeness:**
   ```bash
   # Check if key files exist
   find "student_folder" -name "*Application.java" -o -name "*Controller.java" -o -name "application.yml" | wc -l
   ```

2. **Review key components:**
   - **Main application class**: Check annotations and configuration
   - **Controller classes**: Review REST endpoints and return types
   - **Configuration files**: Check YAML/properties format and content
   - **Service interfaces**: Review method signatures and annotations

3. **Common issues checklist:**
   - [ ] Return `Object` instead of specific types
   - [ ] Missing `@RestController` or incorrect annotations
   - [ ] YAML indentation errors
   - [ ] Missing `@LoadBalanced` on RestTemplate
   - [ ] Incorrect package names
   - [ ] Hard-coded URLs instead of service names
   - [ ] Missing exception handling
   - [ ] No logging statements

4. **Assign scores per dimension:**
   - **项目结构**: Organization, naming, folder structure
   - **功能实现**: Completeness, correctness, edge cases
   - **代码规范**: Naming, formatting, best practices
   - **配置正确性**: Configuration files, annotations
   - **扩展性**: Logging, error handling, maintainability

### Step 5: Feedback and Reporting

**Individual student feedback format:**
```markdown
## [学生姓名] ([学号]) 作业批改分析

### 优点：
1. [Specific positive observation 1]
2. [Specific positive observation 2]
3. [Specific positive observation 3]

### 问题：
1. [Specific issue 1 with line reference]
   - **影响**: [Why this matters]
   - **建议**: [How to fix]
2. [Specific issue 2 with line reference]
   - **影响**: [Why this matters]
   - **建议**: [How to fix]

### 评分：
**项目结构 (20分):** [score]分
**功能实现 (30分):** [score]分
**代码规范 (25分):** [score]分
**配置正确性 (15分):** [score]分
**扩展性 (10分):** [score]分

**总分:** [total]分 ([等级])

**改进建议:**
1. [Actionable improvement 1]
2. [Actionable improvement 2]
3. [Actionable improvement 3]
```

### Step 6: Progress Updates and Mid-Phase Reports

**When 30-50% of students are graded, create mid-phase report:**

```markdown
# [Subject] [Chapter] 作业批改中期报告

## 批改概况
**批改时间**: [date]
**总学生数**: [total]
**已批改**: [graded] ([percentage]%)
**待批改**: [remaining] ([percentage]%)

## 成绩分布统计
[Statistics table]

## 常见问题分析
[Top 3-5 recurring issues]

## 优秀作业特征总结
[Patterns from high-scoring assignments]

## 教学建议
[Recommendations for instruction]

## 后续批改计划
[Remaining work and timeline]
```

### Step 7: Final Summary and Analysis

**After all students are graded:**

1. **Generate final statistics:**
   - Average scores per dimension
   - Distribution across grade levels
   - Most common errors
   - Best practices adoption rates

2. **Create teaching recommendations:**
   - Topics needing reinforcement
   - Common misconceptions
   - Effective teaching strategies observed
   - Suggested improvements for future assignments

3. **Archive completed work:**
   - Move to completed folder
   - Create summary index
   - Backup grading data

## Common Grading Scenarios

### Scenario 1: Incomplete Submissions
**Student only submitted frontend files or partial work**

**Approach:**
- Grade based on what's present
- Note missing components in feedback
- Suggest minimum viable completion
- Consider partial credit for attempted components

### Scenario 2: Copy-Paste or Template Modifications
**Student modified template but didn't understand concepts**

**Approach:**
- Check for understanding vs. rote copying
- Ask conceptual questions in feedback
- Look for inconsistencies that indicate lack of understanding
- Grade comprehension, not just completion

### Scenario 3: Overly Complex or Unnecessary Code
**Student added unnecessary complexity or features**

**Approach:**
- Praise initiative but guide toward simplicity
- Explain YAGNI (You Ain't Gonna Need It) principle
- Suggest refactoring to simpler solutions
- Grade on correctness, not complexity

### Scenario 4: Technical Excellence but Poor Documentation
**Great code but no comments or poor structure**

**Approach:**
- Separate technical score from documentation score
- Emphasize maintainability and teamwork
- Provide specific documentation templates
- Reward technical excellence but note areas for improvement

## Technical Patterns for Common Assignments

### Spring Cloud Microservices Assignments
**Common issues found:**
1. **Type safety**: Returning `Object` instead of `List<Dept>` or specific types
2. **Annotation errors**: Missing `@EnableEurekaClient`, `@EnableFeignClients`
3. **Configuration**: YAML indentation, missing `@LoadBalanced`
4. **Service discovery**: Hard-coded URLs instead of service names
5. **Error handling**: No exception handling or fallback methods
6. **Logging**: Missing system logs for debugging

**Scoring focus areas:**
- Service registration and discovery implementation
- Load balancing configuration
- Circuit breaker patterns (Hystrix)
- Configuration management
- API design and REST conventions

### Web Development Assignments
**Common issues found:**
1. **Security**: No input validation, XSS vulnerabilities
2. **Performance**: N+1 queries, no caching
3. **Accessibility**: Missing ARIA labels, poor semantic HTML
4. **Responsiveness**: Fixed layouts, no mobile support
5. **Code organization**: Spaghetti code, no separation of concerns

## Pitfalls to Avoid

### ⚠️ Don't Assume Uniform Quality
- Students have varying skill levels and backgrounds
- Adjust expectations based on course level and prerequisites
- Provide differentiated feedback (beginner vs. advanced issues)

### ⚠️ Avoid Over-Grading Early Samples
- First few students establish the curve
- Don't be too harsh or too lenient in initial samples
- Recalibrate if needed after 3-4 students

### ⚠️ Maintain Consistency
- Use rubrics and checklists
- Keep notes on borderline decisions
- Review similar cases together for consistency

### ⚠️ Balance Detail with Efficiency
- Provide actionable feedback, not just criticism
- Focus on most important issues (Pareto principle)
- Use templates for common feedback patterns

## Integration with Other Skills

### With `github-code-review`
- Use similar structured feedback formats
- Apply code quality principles
- Borrow review checklist items

### With `writing-plans`
- Create grading plans and schedules
- Break down large grading tasks
- Track progress systematically

## Best Practices

### 1. Start with Clear Rubrics
- Define scoring dimensions upfront
- Share rubrics with students if possible
- Use consistent terminology

### 2. Provide Actionable Feedback
- Specific: "Line 45: Use @RestController instead of @Controller"
- Constructive: "Here's how to fix it"
- Prioritized: "Fix critical issues first, then suggestions"

### 3. Track Progress Systematically
- Update progress files after each batch
- Create checkpoints (25%, 50%, 75%, 100%)
- Generate reports at each checkpoint

### 4. Maintain Audit Trail
- Keep original grading files
- Document scoring decisions
- Save intermediate versions

### 5. Plan for Scalability
- Design templates for different assignment types
- Create reusable grading scripts
- Establish folder structures for multiple classes/terms

## Related Technique: Word Document Automation

For tasks involving programmatic manipulation of Word documents, see the reference files:

- `references/word-doc-automation-win32com.md` — Using win32com to manipulate legacy `.doc` files (find paragraphs, insert/delete content, batch-process multiple documents, handle Chinese text encoding pitfalls). Use this for old-format `.doc` files that python-docx cannot open.

- `references/docx-xml-manipulation.md` — Direct XML manipulation of `.docx` files via zipfile + regex. Use this for complex table structures (教案 teaching plans, course summaries with merged cells) where python-docx falls short. Covers: regex pitfalls with `<w:trPr>`/`<w:tcPr>`, finding all section positions before processing, building new cell content, and user preferences for content placement and class differentiation.

These techniques are useful when you need to:
- Fill in pre-formatted `.doc` or `.docx` templates with course-specific content
- Batch-generate teaching summary documents for multiple courses
- Update existing Word documents with new sections programmatically
- Replace content in specific table cells of教案 (lesson plan) documents

## Quick Reference Commands

### Folder Structure Setup
```bash
# Create grading structure
mkdir -p "$HOME/Desktop/作业批改/[Subject]/[Chapter]"

# List students to grade
find "assignment_folder" -maxdepth 1 -type d | grep -E "学生" | sort

# Count total students
find "assignment_folder" -maxdepth 1 -type d | grep -E "学生" | wc -l
```

### Student Work Examination
```bash
# Check for key files
find "student_folder" -name "*.java" -o -name "*.yml" -o -name "*.yaml" | head -5

# Read main application file
find "student_folder" -name "*Application.java" | head -1 | xargs cat

# Check configuration
find "student_folder" -name "application.yml" -o -name "application.properties" | head -1 | xargs cat
```

### Progress Tracking
```bash
# Count graded students
grep -c "已完成" progress_tracking.md

# Update CSV scores
# Use patch tool to update individual student rows
```

## Remember

**Core workflow:**
1. Setup organized folder structure
2. Create grading templates
3. Grade sample students to establish standards
4. Systematic batch grading with consistent criteria
5. Generate multiple report formats
6. Track progress and create checkpoints
7. Final analysis and teaching recommendations

**Available templates:**
- `templates/grading-spreadsheet-template.csv` - CSV template for student scores
- `references/spring-cloud-grading-patterns.md` - Common issues and scoring patterns for Spring Cloud assignments