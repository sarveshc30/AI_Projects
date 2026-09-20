# Q&A Log — Agent-as-a-Judge RAG Chatbot

_Auto-generated. Each section contains the question, the generated answer, and the raw retrieved chunks._

---

## Q: What is the DevAI dataset, and how many tasks, requirements, and preferences does it contain?
_Asked at 2026-09-20 19:33:11_

### Answer

The DevAI dataset is a curated collection of AI‑development tasks designed for evaluating agentic systems. It comprises **55 distinct tasks**. Across these tasks there are **365 plain‑text requirements** (organized as a directed‑acyclic graph of dependencies) and **125 preferences**, which serve as softer, optional criteria.  

*Source: Passage 3 (page 3) – “DevAI consists of a curated set of 55 tasks… for a total of 365 requirements… for a total of 125 preferences.”*

### Retrieved Chunks

**[Chunk 1/4]** Page 3 | ID: `3-2` | Distance: 0.3716

```
DevAI is structured so that an agentic system starts by receiving a user query to begin development. The
system is then evaluated on how well it meets the requirements, with preferences serving as optional, softer
criteria. An example of one of the DevAI tasks can be seen in Figure 3.
The tasks in DevAI are relatively small-scale but cover commonly used key development techniques. As shown
in Figure 2, our tasks are tagged and cover a variety of key areas in AI: supervised learning, reinforcement
learning, computer vision, natural language processing, generative models, and others. Each of the tasks
is a real-world problem that could be given to a research engineer, while simultaneously being relatively
```

**[Chunk 2/4]** Page 22 | ID: `22-5` | Distance: 0.3929

```
Manual refinements were necessary to ensure the accuracy and clarity of DevAI. We perform two rounds of
comprehensive review and edits on DevAI, each round being done by a different participant. During these
manual refinements, we focus on the logical consistency of our queries and requirements, the correctness and
ambiguity of the language, and the applicability of the content to the task domain. We identified a moderate
number of errors in our dataset during the review.
E.5 Analyse the dataset
We categorized each requirement based on its focus, whether it was related to the data set, the machine
learning method, visualization, metrics, HCI, or data processing. While this approach provides a useful
```

**[Chunk 3/4]** Page 3 | ID: `3-1` | Distance: 0.4010

```
here reflects the fact that it dominates many machine learning applications. (4) SVM classifiers (Cortes, 1995) and
LSTM models (Hochreiter, 1997) are two of the most widely used architectures—a fact reflected by DevAI.
2.2 The DevAI Dataset
Motivated by the ideas outlined above, we propose the DevAI dataset. DevAI consists of a curated set of 55
tasks, each defined by (1) a plain text user query that describes an AI development task; (2) a set of plain
text requirements (for a total of 365 requirements), each with a set of dependencies connecting them to other
requirements; and (3) a set of preferences (for a total of 125 preferences) which represent softer requirements.
DevAI is structured so that an agentic system starts by receiving a user query to begin development. The
```

**[Chunk 4/4]** Page 3 | ID: `3-3` | Distance: 0.4245

```
is a real-world problem that could be given to a research engineer, while simultaneously being relatively
inexpensive computationally to run so as to reduce the cost of evaluating a method on this benchmark. Details
of the sample collection and human labeling process for DevAI are provided in Appendix E.
The requirements belonging to each task represent a milestone in the comprehensive development process and
are arranged as a directed acyclic graph (similar to the work by He et al. (2021)), with requirements such
as visualizing results depending on correct data loading and modeling. This allows for more comprehensive
non-sparse feedback than a binary success metric. Furthermore, the inclusion of hierarchical requirements
```

---

## Q: What percentage of evaluation time and cost does Agent-as-a-Judge save compared to using three human experts?
_Asked at 2026-09-20 19:33:13_

### Answer

Agent‑as‑a‑Judge requires only **2.36 % of the evaluation time** and **2.29 % of the cost** of a three‑human‑expert (Human‑as‑a‑Judge) evaluation.  In other words, it saves roughly **97.6 % of the time** and **97.7 % of the cost** (Page 10, Passage 1).

### Retrieved Chunks

**[Chunk 1/4]** Page 10 | ID: `10-0` | Distance: 0.2278

```
to the requirements. However, adding retrieve does not provide a significant benefit in this case. In contrast,
as shown in Table 3, the judgment of MetaGPT and GPT-Pilot indicates that retrieve is useful, as the
trajectory provides additional valuable information.
4.4 Cost Analysis
The Human-as-a-Judge took the three evaluators a self-reported total of 86 .5 hours. With a 15 USD minimum
wage (assuming this would buy a subject expert in AI), a full evaluation under DevAI would cost around
1297.50 USD. In comparison, Agent-as-a-Judge cost only 30 .58 USD in API calls and took only 118 .43
minutes—2.29% of the cost and 2 .36% of the time of Human-as-a-Judge. LLM-as-a-Judge was faster at 10 .99
```

**[Chunk 2/4]** Page 7 | ID: `7-2` | Distance: 0.2726

```
is particularly important when there are only a few evalu-
ators, as majority voting with a small group can still lead
to errors (around 5% compared to consensus evaluation,
as shown in Figure 5). The second approach involves
assembling a larger panel of experts (more is better when
their accuracy exceeds 50% (Grofman et al., 1983)), with
over 5 people recommended by Hastie and Kameda (2005);
Larrick and Soll (2006), and relying on a majority vote.
However, due to the high cost of engaging more experts
and the fact that this is not always feasible in practice,
we argue for the former.
4 Agent-as-a-Judge: Evaluating Agents with Agents
Human evaluation, while somewhat reliable, is time-consuming and requires substantial expertise. To address
```

**[Chunk 3/4]** Page 9 | ID: `9-3` | Distance: 0.2858

```
evaluations, especially in complex scenarios.
PR Curves Judging developer agents is a class-
imbalanced task, where meeting requirements is
much rarer than failing. Metrics like judge shift
and alignment rate can be misleading. For example,
since MetaGPT rarely meets requirements, LLM-as-a-Judge easily identifies most cases as negative (achieving
84.15% in the black-box setting). PR Curves offer a clearer performance measure by balancing precision and
recall. Agent-as-a-Judge even outperforms any single human evaluator on OpenHands and aligns closest with
majority voting. This shows that, in some cases, Agent-as-a-Judge can nearly replace human evaluators.
4.3 Ablations For Agent-as-a-Judge
```

**[Chunk 4/4]** Page 17 | ID: `17-1` | Distance: 0.3057

```
Description: In the first level of experiments, we select three popular open-source developer
agents: MetaGPT, GPT-Pilot, and OpenHands. These agents are evaluated on the DevAI tasks
to establish performance baselines.
■ Step 4: Conducting Human-as-a-Judge Evaluation
Description: We conduct a Human-as-a-Judge experiment, where three human experts assess
the performance of the developer agents on the same DevAI tasks.
■ Step 5: Human-as-a-Judge Analysis (Experiment Level 2)
Description: In the second level of experiments, we statistically analyze the results of Human-as-
a-Judge evaluations, focusing on the costs of human labor and potential biases, highlighting the
challenges of relying on human evaluation for complex tasks.
■ Step 6: Agent-as-a-Judge Implementation
```

---

## Q: According to Section 4.4 (Cost Analysis), how much did Agent-as-a-Judge cost and how long did it take, compared to Human-as-a-Judge?
_Asked at 2026-09-20 19:33:14_

### Answer

According to Section 4.4 (Cost Analysis), the Agent‑as‑a‑Judge evaluation cost **$30.58** in API calls and took **118.43 minutes** to run. This represents only **2.29 % of the monetary cost** and **2.36 % of the time** required by the Human‑as‑a‑Judge, which took **86.5 hours** and cost about **$1,297.50** (Page 10).

### Retrieved Chunks

**[Chunk 1/6]** Page 10 | ID: `10-0` | Distance: 0.2828

```
to the requirements. However, adding retrieve does not provide a significant benefit in this case. In contrast,
as shown in Table 3, the judgment of MetaGPT and GPT-Pilot indicates that retrieve is useful, as the
trajectory provides additional valuable information.
4.4 Cost Analysis
The Human-as-a-Judge took the three evaluators a self-reported total of 86 .5 hours. With a 15 USD minimum
wage (assuming this would buy a subject expert in AI), a full evaluation under DevAI would cost around
1297.50 USD. In comparison, Agent-as-a-Judge cost only 30 .58 USD in API calls and took only 118 .43
minutes—2.29% of the cost and 2 .36% of the time of Human-as-a-Judge. LLM-as-a-Judge was faster at 10 .99
```

**[Chunk 2/6]** Page 9 | ID: `9-3` | Distance: 0.4327

```
evaluations, especially in complex scenarios.
PR Curves Judging developer agents is a class-
imbalanced task, where meeting requirements is
much rarer than failing. Metrics like judge shift
and alignment rate can be misleading. For example,
since MetaGPT rarely meets requirements, LLM-as-a-Judge easily identifies most cases as negative (achieving
84.15% in the black-box setting). PR Curves offer a clearer performance measure by balancing precision and
recall. Agent-as-a-Judge even outperforms any single human evaluator on OpenHands and aligns closest with
majority voting. This shows that, in some cases, Agent-as-a-Judge can nearly replace human evaluators.
4.3 Ablations For Agent-as-a-Judge
```

**[Chunk 3/6]** Page 18 | ID: `18-1` | Distance: 0.4372

```
Level 2
⁄leafExperiment 2a: Error analysis of human evaluations (Section 3.2)
Level 3
⁄leafExperiment 3a: AI judge baselines (Section 4.2)
⁄leafExperiment 3b: Ablation studies for Agent-as-a-Judge (Section 4.3)
B.2 Judges and Subjects of Evaluation
The following table summarizes the judge and the subject being evaluated in each experiment:
Experiment Who is the Judge? Who is being Judged?
Section 2.3 Human Developer Agents
Section 3.1 Human Developer Agents
Section 3.2 Human Human
Section 4.2 (1) LLM-as-a-Judge (1) Developer Agents
(2) Agent-as-a-Judge (2) Developer Agents
(3) Human (3) LLM-as-a-Judge
(4) Human (4) Agent-as-a-Judge
Section 4.3 Human Agent-as-a-Judge
19
```

**[Chunk 4/6]** Page 17 | ID: `17-1` | Distance: 0.4445

```
Description: In the first level of experiments, we select three popular open-source developer
agents: MetaGPT, GPT-Pilot, and OpenHands. These agents are evaluated on the DevAI tasks
to establish performance baselines.
■ Step 4: Conducting Human-as-a-Judge Evaluation
Description: We conduct a Human-as-a-Judge experiment, where three human experts assess
the performance of the developer agents on the same DevAI tasks.
■ Step 5: Human-as-a-Judge Analysis (Experiment Level 2)
Description: In the second level of experiments, we statistically analyze the results of Human-as-
a-Judge evaluations, focusing on the costs of human labor and potential biases, highlighting the
challenges of relying on human evaluation for complex tasks.
■ Step 6: Agent-as-a-Judge Implementation
```

**[Chunk 5/6]** Page 0 | ID: `0-5` | Distance: 0.4520

```
a better evaluation with a human is prohibitively expensive. We instead propose that agentic systems should
be used to evaluate agentic systems. Inspired by LLM-as-a-Judge (Zheng et al., 2024; Fu et al., 2023; Chen
et al., 2024b), which uses LLMs to evaluate LLMs, we call this framework Agent-as-a-Judge, of which it is
1
arXiv:2410.10934v2  [cs.AI]  16 Oct 2024
```

**[Chunk 6/6]** Page 9 | ID: `9-1` | Distance: 0.4585

```
Judge Shift Judge Shift measures deviation from the Human-as-a-Judge consensus results, with lower values
indicating a closer alignment. As shown in table 3, Agent-as-a-Judge consistently outperforms LLM-as-a-Judge
across tasks, particularly those with task dependencies. For example, in Requirement (I), Agent-as-a-Judge
shows a Judge Shift as low as 0 .27%, while LLM-as-a-Judge reaches 31 .24% for OpenHands. This underscores
Agent-as-a-Judge’s stability and suitability for meeting task requirements. Furthermore, in the gray-box
setting, both Agent-as-a-Judge and LLM-as-a-Judge show even better results than their performance in the
black-box setting.
Figure 7 PR Curves comparing judge Methods.
Alignment Rate The Alignment Rate reflects how
```

---

## Q: Which three open-source agentic frameworks were benchmarked on DevAI?
_Asked at 2026-09-20 19:33:15_

### Answer

The three open‑source code‑generation agentic frameworks benchmarked on DevAI are **MetaGPT**, **GPT‑Pilot**, and **OpenHands**【Passage 2 | Page 1】.

### Retrieved Chunks

**[Chunk 1/4]** Page 2 | ID: `2-0` | Distance: 0.3581

```
In addition, considering the evaluation cost, Agent-as-a-Judge saves 97.72% of the time and 97.64% of the
cost compared to involving three human experts.
In summary, the principal contributions of this work are:
• We release the DevAI dataset, which consists of 55 comprehensive AI development tasks with accompanying
tags, individual hierarchical requirements, and individual preferences.
• We benchmark three top open-source code generation agentic frameworks in DevAI, providing a more
comprehensive analysis than previous evaluations of them.
• We introduce the general Agent-as-a-Judge concept, allowing agentic systems a fair and rich evaluation
without the traditional costs associated with human involvement.
```

**[Chunk 2/4]** Page 1 | ID: `1-6` | Distance: 0.3640

```
Equally concerning, recent work has begun to introduce mechanisms designed specifically for the individual
tasks in the SWE-Bench dataset, leading to a lack of real-world generalization and violating Goodhart’s law:
“When a measure becomes a target, it ceases to be a good measure” (Goodhart, 1976).
To address the aforementioned issues with the current benchmarks in code generation, we introduce DevAI:
the AI Developer Dataset, which contains 55 real-world comprehensive AI app development tasks created
by expert annotators. We apply three leading open-source code-generating agentic frameworks to the tasks
in DevAI: MetaGPT (Hong et al., 2024b), GPT-Pilot (Pythagora.io, 2023), and OpenHands (Wang et al.,
```

**[Chunk 3/4]** Page 10 | ID: `10-2` | Distance: 0.3726

```
applied to directly imitate software companies (Hong et al., 2024b; Qian et al., 2024a), debug code (Yang
et al., 2024a), run data science methods (Guo et al., 2024; Hong et al., 2024a; Li et al., 2024; Qiao et al.,
2023), and even write academic papers (Lu et al., 2024a).
Benchmarks for AI developments Benchmarks like MLAgentBench (Huang et al., 2024), ML-Bench (Liu
et al., 2023d), SUPER (Bogin et al., 2024), DS-bench (Jing et al., 2024), and MLE-Bench (Chan et al., 2024)
all focus on benchmarking agentic systems using AI tasks. However, DevAI distinguishes itself from all of
these by focusing on realistic user queries that target a complete development cycle. It further includes
a more comprehensive evaluation with multiple hierarchical requirements and preferences for each task.
```

**[Chunk 4/4]** Page 17 | ID: `17-0` | Distance: 0.3960

```
A Outline of this Paper
Paper: Agent-as-a-Judge: Evaluating Agents with Agents
Key Logic
■ Step 1: Concept Proposal
Description: We propose the Agent-as-a-Judge concept, an extension of the LLM-as-a-Judge
framework, aimed at evaluating agentic systems using other agentic systems.
■ Step 2: Dataset Creation
Description: To address the lack of suitable datasets for evaluating agentic systems in automated
AI development, we introduce DevAI, a new dataset consisting of 55 realistic AI code generation
tasks. This also serves as a testbed for the Agent-as-a-Judge proof-of-concept.
■ Step 3: Baseline Evaluation of Developer Agents (Experiment Level 1)
Description: In the first level of experiments, we select three popular open-source developer
```

---

## Q: What is the average cost and average time for OpenHands?
_Asked at 2026-09-20 19:33:16_

### Answer

The paper reports that OpenHands incurs an **average cost of $6.38** and an **average development time of 362.41 seconds** (≈6 minutes) per task【Passage 3 | Page 5】.

### Retrieved Chunks

**[Chunk 1/6]** Page 4 | ID: `4-3` | Distance: 0.4875

```
of 1800 seconds to solve each task and were forcefully halted if they exceeded this time limit (we imposed
this constraint, which was visible to the AI developers, as detailed in Appendix I). We capture the outputs
generated during the automated development process, including code, files, and other artifacts. Additionally,
we record key decisions and actions made by the agentic systems through some custom instrumentation code,
resulting in a development trajectory for each of the agentic systems.
Analysis The basic statistics are shown in Table 1. MetaGPT is the most cost-efficient (1 .19 USD), while
OpenHands is the most expensive (6 .38 USD). In terms of development time, OpenHands completes tasks
5
```

**[Chunk 2/6]** Page 5 | ID: `5-1` | Distance: 0.5449

```
in an average of 362 .41s, while GPT-Pilot takes the longest at 1622 .38s. On average, a full evaluation on
DevAI with one of these three took around 210 .65 USD and 14 hours to perform. While running, GPT-Pilot
generates the most output tokens at 59707 tokens, whereas OpenHands processed the most at 1252482 tokens
while producing the fewest at 8457 tokens. This suggests that OpenHands’s internal communication is more
complicated but is more parsimonious in its decisions.
MetaGPT, while being the most cost-effective, generates fewer saved code files (0 .42), suggesting it may be
less inclined to save files. In contrast, GPT-Pilot generates the most saved files (3 .84), reflecting a more
```

**[Chunk 3/6]** Page 5 | ID: `5-0` | Distance: 0.6263

```
Table 1 Preliminary Statistics of AI Developers. We compare three leading open-source code agents using metrics
such as average cost, average time, and the average number of generated files.
Metric MetaGPT (Hong et al., 2024b) GPT-Pilot (Pythagora.io, 2023) OpenHands (Wang et al., 2024d)
Basic Statistics
Version Data Interpreter (Hong et al., 2024a) 0.2.13 CodeAct v1.9 (Wang et al., 2024c)
(1) Average Cost $1.19 $3.92 $6.38
(2) Average Time 775.29s 1622.38s 362.41s
(3) Average Input Tokens 152863 606707 1252482
(4) Average Output Tokens 28546 59707 8457
(5) Average Saved Code Files 0.42 3.84 2.53
(6) Average Saved Code Lines 11.15 273.33 96.56
(7) Average Saved Files 4.42 5.91 3.60
in an average of 362 .41s, while GPT-Pilot takes the longest at 1622 .38s. On average, a full evaluation on
```

**[Chunk 4/6]** Page 5 | ID: `5-2` | Distance: 0.6914

```
less inclined to save files. In contrast, GPT-Pilot generates the most saved files (3 .84), reflecting a more
prolific output. The difference in saved code lines, with GPT-Pilot saving 273 .33 lines versus MetaGPT’s
11.15, underscores GPT-Pilot’s extensive output. Meanwhile, OpenHands, despite handling larger inputs,
seems less focused on executing code to generate files, as evidenced by its lower file output (2 .53 saved files).
These statistics align with real user experiences (as discussed in Appendix F).
Evaluations Note that the results in Table 1 are not directly indicative of performance but provide valuable
insights into the practical utility of DevAI and the performance of AI developers. The generated workspaces
```

**[Chunk 5/6]** Page 6 | ID: `6-1` | Distance: 0.6929

```
evaluation and their self-reported post-hoc descriptions of how they resolved ambiguities are reported in
Figure 12 in Appendix H.
After the initial round of human evaluations (which totaled an estimated total of 58 human hours), we asked
our evaluators to discuss and reach a consensus on their assessments (which took an estimated total of 28 .5
additional human hours). This consensus, achieved after long sessions of debate, was used as the final human
evaluation result for each method.
Performance Analysis The results of this experiment are shown in Table 2. We found that the two best-
performing methods (GPT-Pilot and OpenHands) could satisfy about 29% of the requirements (or around
```

**[Chunk 6/6]** Page 10 | ID: `10-0` | Distance: 0.7230

```
to the requirements. However, adding retrieve does not provide a significant benefit in this case. In contrast,
as shown in Table 3, the judgment of MetaGPT and GPT-Pilot indicates that retrieve is useful, as the
trajectory provides additional valuable information.
4.4 Cost Analysis
The Human-as-a-Judge took the three evaluators a self-reported total of 86 .5 hours. With a 15 USD minimum
wage (assuming this would buy a subject expert in AI), a full evaluation under DevAI would cost around
1297.50 USD. In comparison, Agent-as-a-Judge cost only 30 .58 USD in API calls and took only 118 .43
minutes—2.29% of the cost and 2 .36% of the time of Human-as-a-Judge. LLM-as-a-Judge was faster at 10 .99
```

---

## Q: Which system is the most cost-efficient and which is the most expensive?
_Asked at 2026-09-20 19:33:19_

### Answer

The most cost‑efficient system is **MetaGPT** (average cost ≈ $1.19), while the most expensive system is **OpenHands** (average cost ≈ $6.38)【Page 5, ID 5‑0】【Page 4, ID 4‑3】.

### Retrieved Chunks

**[Chunk 1/6]** Page 5 | ID: `5-1` | Distance: 0.6396

```
in an average of 362 .41s, while GPT-Pilot takes the longest at 1622 .38s. On average, a full evaluation on
DevAI with one of these three took around 210 .65 USD and 14 hours to perform. While running, GPT-Pilot
generates the most output tokens at 59707 tokens, whereas OpenHands processed the most at 1252482 tokens
while producing the fewest at 8457 tokens. This suggests that OpenHands’s internal communication is more
complicated but is more parsimonious in its decisions.
MetaGPT, while being the most cost-effective, generates fewer saved code files (0 .42), suggesting it may be
less inclined to save files. In contrast, GPT-Pilot generates the most saved files (3 .84), reflecting a more
```

**[Chunk 2/6]** Page 5 | ID: `5-0` | Distance: 0.7064

```
Table 1 Preliminary Statistics of AI Developers. We compare three leading open-source code agents using metrics
such as average cost, average time, and the average number of generated files.
Metric MetaGPT (Hong et al., 2024b) GPT-Pilot (Pythagora.io, 2023) OpenHands (Wang et al., 2024d)
Basic Statistics
Version Data Interpreter (Hong et al., 2024a) 0.2.13 CodeAct v1.9 (Wang et al., 2024c)
(1) Average Cost $1.19 $3.92 $6.38
(2) Average Time 775.29s 1622.38s 362.41s
(3) Average Input Tokens 152863 606707 1252482
(4) Average Output Tokens 28546 59707 8457
(5) Average Saved Code Files 0.42 3.84 2.53
(6) Average Saved Code Lines 11.15 273.33 96.56
(7) Average Saved Files 4.42 5.91 3.60
in an average of 362 .41s, while GPT-Pilot takes the longest at 1622 .38s. On average, a full evaluation on
```

**[Chunk 3/6]** Page 34 | ID: `34-1` | Distance: 0.7275

```
to display the d et ec ti on results . Finally , evaluate the model ' s
p e r f o r m a n c e , i nc lu di ng metrics such as mAP and i nf er en ce time , and save
the e v a l u a t i o n results to ` results / metrics / m o d e l _ p e r f o r m a n c e . txt`. The
system should properly manage the launch and t e r m i n a t i o n of the
S tr ea mli t a p p l i c a t i o n to prevent u n n e c e s s a r y resource usage .\ n \ nThis is
a task that requires you to write , execute , and save source code . You
have a hard time limit of 3 0 minutes to produce your p r o g r a m m a t i c
solution to the given task . This time limit includes ex ec ut io n time .
The quality of your solution will be judged based on what you left in
```

**[Chunk 4/6]** Page 38 | ID: `38-0` | Distance: 0.7459

```
K Ablations of Agent-as-a-Judge
K.1 Component Abalations
Table 5 Component Ablation Studies for Agent-as-a-Judge. We analyze the impact of sequentially adding various
components (ask, graph, read, locate, retrieve, planning, memory, and search) on the performance of Agent-as-a-
Judge for judging OpenHands.
Metric + ask + graph + read + locate + search + retrieve + planning + memory
Agent-as-a-Judge Performance
Alignment Rate 65.03% 75.95% 82.24% 90.44% 86.06% 90.16% 88.52% 87.97%
Analysis We designed 8 modular components for the Agent-as-a-Judge system. In the Table 5, components
are added progressively from left to right. If the addition of a component led to a significant performance drop,
```

**[Chunk 5/6]** Page 4 | ID: `4-3` | Distance: 0.7463

```
of 1800 seconds to solve each task and were forcefully halted if they exceeded this time limit (we imposed
this constraint, which was visible to the AI developers, as detailed in Appendix I). We capture the outputs
generated during the automated development process, including code, files, and other artifacts. Additionally,
we record key decisions and actions made by the agentic systems through some custom instrumentation code,
resulting in a development trajectory for each of the agentic systems.
Analysis The basic statistics are shown in Table 1. MetaGPT is the most cost-efficient (1 .19 USD), while
OpenHands is the most expensive (6 .38 USD). In terms of development time, OpenHands completes tasks
5
```

**[Chunk 6/6]** Page 33 | ID: `33-1` | Distance: 0.7503

```
" o u t p u t _ t o k e n s " ,
" model " ,
" cost " ,
" l l m _ i n f e r e n c e _ t i m e " ,
" s t e p _ e x e c u t i o n _ t i m e "
]
} ,
" a c c u m u l a t e d _ u s a g e " : {
" type " : " object " ,
" p r o p e r t i e s " : {
" a c c u m u l a t e d _ c o s t " : {
" type " : " number " ,
" d e s c r i p t i o n " : " The total cost of the t r a j e c t o r y up to this step , in
USD . "
} ,
" a c c u m u l a t e d _ t i m e " : {
" type " : " number " ,
" d e s c r i p t i o n " : " The total time taken by the agent to complete the
t r a j e c t o r y up to this step , in seconds . "
}
} ,
" required " : [
" a c c u m u l a t e d _ c o s t " ,
" a c c u m u l a t e d _ t i m e "
]
}
} ,
```

---

## Q: What was GPT-Pilot's 'Requirements Met (Independent)' percentage under Human-as-a-Judge?
_Asked at 2026-09-20 19:33:31_

### Answer

GPT‑Pilot satisfied **44.80 %** of the requirements on independent tasks (Requirements Met (I)) when evaluated by Human‑as‑a‑Judge【Passage 1 | Page 5】.

### Retrieved Chunks

**[Chunk 1/6]** Page 5 | ID: `5-4` | Distance: 0.4258

```
Table 2 Human-as-a-Judge for AI Developers. (I) and (D) represent independent performance versus performance
considering task dependencies.
 indicates multiple experts evolved, and
 means the evaluations use white-box
testing (allowing access to the generated workspace, human-collected trajectories, and open-source codebases). The
results were derived from expert judgments and deliberations (see Appendix H).
Metric MetaGPT (Hong et al., 2024b) GPT-Pilot (Pythagora.io, 2023) OpenHands (Wang et al., 2024d)
/
 Human-as-a-Judge
(A) Requirements Met (I) 22.13% 44.80% 42.89%
(B) Requirements Met (D) 6.55% 28.96% 28.68%
(C) Self-Termination 41.81% 5.45% 54.54%
(D) Task Solve Rate 0.00% 1.81% 1.81%
6
```

**[Chunk 2/6]** Page 6 | ID: `6-1` | Distance: 0.4372

```
evaluation and their self-reported post-hoc descriptions of how they resolved ambiguities are reported in
Figure 12 in Appendix H.
After the initial round of human evaluations (which totaled an estimated total of 58 human hours), we asked
our evaluators to discuss and reach a consensus on their assessments (which took an estimated total of 28 .5
additional human hours). This consensus, achieved after long sessions of debate, was used as the final human
evaluation result for each method.
Performance Analysis The results of this experiment are shown in Table 2. We found that the two best-
performing methods (GPT-Pilot and OpenHands) could satisfy about 29% of the requirements (or around
```

**[Chunk 3/6]** Page 10 | ID: `10-0` | Distance: 0.4569

```
to the requirements. However, adding retrieve does not provide a significant benefit in this case. In contrast,
as shown in Table 3, the judgment of MetaGPT and GPT-Pilot indicates that retrieve is useful, as the
trajectory provides additional valuable information.
4.4 Cost Analysis
The Human-as-a-Judge took the three evaluators a self-reported total of 86 .5 hours. With a 15 USD minimum
wage (assuming this would buy a subject expert in AI), a full evaluation under DevAI would cost around
1297.50 USD. In comparison, Agent-as-a-Judge cost only 30 .58 USD in API calls and took only 118 .43
minutes—2.29% of the cost and 2 .36% of the time of Human-as-a-Judge. LLM-as-a-Judge was faster at 10 .99
```

**[Chunk 4/6]** Page 1 | ID: `1-7` | Distance: 0.4683

```
in DevAI: MetaGPT (Hong et al., 2024b), GPT-Pilot (Pythagora.io, 2023), and OpenHands (Wang et al.,
2024d). We evaluate their performance using human judges (a painstaking process), LLM-as-a-Judge (Zheng
et al., 2024), and our Agent-as-a-Judge framework.
Through human evaluation, we found that GPT-Pilot and OpenHands were each able to satisfy about 29%
of the task requirements in DevAI, but only one full task—showing that DevAI presents a good level of
challenge to current systems. When comparing our human judges with our automatic Agent-as-a-Judge
framework, we found that Agent-as-a-Judge aligns more closely with the consensus of our human judges (90%)
as compared to LLM-as-a-Judge (70%) in all cases tested. In addition, we find that it aligns more closely
```

**[Chunk 5/6]** Page 6 | ID: `6-2` | Distance: 0.4727

```
performing methods (GPT-Pilot and OpenHands) could satisfy about 29% of the requirements (or around
44% if prerequisites are ignored) but only on one task could they meet all the requirements. This highlights
that DevAI offers a considerable but appropriate level of challenge for current and future methods. Moreover,
the fulfillment of intermediate requirements aligns with our expectations, as discussed in Section 2, that
DevAI provides richer feedback by uncovering how agentic systems falter during the process instead of just
focusing on a single performance metric at the end.
3.2 Judging Human-as-a-Judge
Figure 4 Between the three human evaluators, a large amount of disagreement was observed in their individual
```

**[Chunk 6/6]** Page 8 | ID: `8-0` | Distance: 0.4757

```
Table 3 AI Judges and Their Shift/Alignment with Human-as-a-Judge. We compare the results of LLM-as-a-Judge
and Agent-as-a-Judge with Human-as-a-Judge. (I) represents performance on independent tasks, while (D) represents
performance considering task dependencies. Note:
 gray-box settings use carefully manually collected trajectory
data (which is nearly inaccessible in practical situations, see Appendix J). In contrast,
 black-box setting doesn’t
need to access to such data. The red scores represent the absolute judge shift compared with Human-as-a-Judge ( e.g.,
2.74%).
Metric MetaGPT (Hong et al., 2024b) GPT-Pilot (Pythagora.io, 2023) OpenHands (Wang et al., 2024d)
LLM-as-a-Judge
(a) Requirements Met (I) 19.39% (2.74%) 12.56% (32.24%) 11.47% (31.42%)
```

---

## Q: What was MetaGPT's Task Solve Rate?
_Asked at 2026-09-20 19:33:42_

### Answer

I could not find this information in the provided paper.

### Retrieved Chunks

**[Chunk 1/6]** Page 5 | ID: `5-1` | Distance: 0.4719

```
in an average of 362 .41s, while GPT-Pilot takes the longest at 1622 .38s. On average, a full evaluation on
DevAI with one of these three took around 210 .65 USD and 14 hours to perform. While running, GPT-Pilot
generates the most output tokens at 59707 tokens, whereas OpenHands processed the most at 1252482 tokens
while producing the fewest at 8457 tokens. This suggests that OpenHands’s internal communication is more
complicated but is more parsimonious in its decisions.
MetaGPT, while being the most cost-effective, generates fewer saved code files (0 .42), suggesting it may be
less inclined to save files. In contrast, GPT-Pilot generates the most saved files (3 .84), reflecting a more
```

**[Chunk 2/6]** Page 4 | ID: `4-3` | Distance: 0.4819

```
of 1800 seconds to solve each task and were forcefully halted if they exceeded this time limit (we imposed
this constraint, which was visible to the AI developers, as detailed in Appendix I). We capture the outputs
generated during the automated development process, including code, files, and other artifacts. Additionally,
we record key decisions and actions made by the agentic systems through some custom instrumentation code,
resulting in a development trajectory for each of the agentic systems.
Analysis The basic statistics are shown in Table 1. MetaGPT is the most cost-efficient (1 .19 USD), while
OpenHands is the most expensive (6 .38 USD). In terms of development time, OpenHands completes tasks
5
```

**[Chunk 3/6]** Page 26 | ID: `26-1` | Distance: 0.5096

```
modularization. This enhances its appeal for users focused on task clarity and modular breakdowns. However,
in practical deployments, MetaGPT tends to be less aggressive in file management and preservation, potentially
due to its core positioning as a data analysis tool, which does not prioritize persistent state management.
Similarly, OpenDevin demonstrates a notable overconfidence in its code generation, frequently skipping the
critical step of post-generation code execution, requiring users to intervene manually.
GPT-Pilot (Pythagora.io, 2023), praised for its detailed task delegation via over 20 specialized agents, suffers
from reduced interactivity due to an overly granular division of responsibilities, resulting in a more fragmented
```

**[Chunk 4/6]** Page 1 | ID: `1-7` | Distance: 0.5133

```
in DevAI: MetaGPT (Hong et al., 2024b), GPT-Pilot (Pythagora.io, 2023), and OpenHands (Wang et al.,
2024d). We evaluate their performance using human judges (a painstaking process), LLM-as-a-Judge (Zheng
et al., 2024), and our Agent-as-a-Judge framework.
Through human evaluation, we found that GPT-Pilot and OpenHands were each able to satisfy about 29%
of the task requirements in DevAI, but only one full task—showing that DevAI presents a good level of
challenge to current systems. When comparing our human judges with our automatic Agent-as-a-Judge
framework, we found that Agent-as-a-Judge aligns more closely with the consensus of our human judges (90%)
as compared to LLM-as-a-Judge (70%) in all cases tested. In addition, we find that it aligns more closely
```

**[Chunk 5/6]** Page 6 | ID: `6-1` | Distance: 0.5320

```
evaluation and their self-reported post-hoc descriptions of how they resolved ambiguities are reported in
Figure 12 in Appendix H.
After the initial round of human evaluations (which totaled an estimated total of 58 human hours), we asked
our evaluators to discuss and reach a consensus on their assessments (which took an estimated total of 28 .5
additional human hours). This consensus, achieved after long sessions of debate, was used as the final human
evaluation result for each method.
Performance Analysis The results of this experiment are shown in Table 2. We found that the two best-
performing methods (GPT-Pilot and OpenHands) could satisfy about 29% of the requirements (or around
```

**[Chunk 6/6]** Page 4 | ID: `4-2` | Distance: 0.5328

```
n.ai/blog/introducing-devin. As this example shows, task requirements in DevAI are structured as a Directed
Acyclic Graph (DAG), with nodes representing individual requirements and directed edges showing dependencies.
More examples are in Appendix G.
will refer to as “ AI developers ”): MetaGPT (Hong et al., 2024b), GPT-Pilot (Pythagora.io, 2023), and
OpenHands (Wang et al., 2024d)—all selected for their strong community acceptance (each having over 30,000
stars on GitHub).
Experiment Setup All of these three systems require a language model as a back-end engine, for which
we use gpt-4o-2024-05-13, a state-of-the-art language model. These AI developers were given a time-limit
of 1800 seconds to solve each task and were forcefully halted if they exceeded this time limit (we imposed
```

---

## Q: In the black-box setting, what Alignment Rate did Agent-as-a-Judge vs. LLM-as-a-Judge achieve when evaluating OpenHands?
_Asked at 2026-09-20 19:33:55_

### Answer

In the black‑box setting for OpenHands, **Agent‑as‑a‑Judge achieved an Alignment Rate of 90.44 %**, while **LLM‑as‑a‑Judge achieved an Alignment Rate of 60.38 %**【Passage 1, Page 9】.

### Retrieved Chunks

**[Chunk 1/6]** Page 9 | ID: `9-2` | Distance: 0.2585

```
black-box setting.
Figure 7 PR Curves comparing judge Methods.
Alignment Rate The Alignment Rate reflects how
closely the AI Judges’ evaluations align with human
consensus across all 365 requirements. It is defined
as the percentage of requirement evaluations that
are the same as the Human-as-a-Judge consensus
evaluation. Compared to LLM-as-a-Judge, Agent-
as-a-Judge consistently achieves a higher Alignment
Rate, closely matching human judgments. For
example, when evaluating OpenHands, Agent-as-a-
Judge reaches 92.07% and 90.44%, surpassing LLM-
as-a-Judge’s 70.76% and 60 .38% in both gray-box
and black-box settings. This shows that Agent-as-a-
Judge produces more accurate and human-aligned
evaluations, especially in complex scenarios.
PR Curves Judging developer agents is a class-
```

**[Chunk 2/6]** Page 9 | ID: `9-1` | Distance: 0.2647

```
Judge Shift Judge Shift measures deviation from the Human-as-a-Judge consensus results, with lower values
indicating a closer alignment. As shown in table 3, Agent-as-a-Judge consistently outperforms LLM-as-a-Judge
across tasks, particularly those with task dependencies. For example, in Requirement (I), Agent-as-a-Judge
shows a Judge Shift as low as 0 .27%, while LLM-as-a-Judge reaches 31 .24% for OpenHands. This underscores
Agent-as-a-Judge’s stability and suitability for meeting task requirements. Furthermore, in the gray-box
setting, both Agent-as-a-Judge and LLM-as-a-Judge show even better results than their performance in the
black-box setting.
Figure 7 PR Curves comparing judge Methods.
Alignment Rate The Alignment Rate reflects how
```

**[Chunk 3/6]** Page 9 | ID: `9-3` | Distance: 0.3607

```
evaluations, especially in complex scenarios.
PR Curves Judging developer agents is a class-
imbalanced task, where meeting requirements is
much rarer than failing. Metrics like judge shift
and alignment rate can be misleading. For example,
since MetaGPT rarely meets requirements, LLM-as-a-Judge easily identifies most cases as negative (achieving
84.15% in the black-box setting). PR Curves offer a clearer performance measure by balancing precision and
recall. Agent-as-a-Judge even outperforms any single human evaluator on OpenHands and aligns closest with
majority voting. This shows that, in some cases, Agent-as-a-Judge can nearly replace human evaluators.
4.3 Ablations For Agent-as-a-Judge
```

**[Chunk 4/6]** Page 8 | ID: `8-0` | Distance: 0.3629

```
Table 3 AI Judges and Their Shift/Alignment with Human-as-a-Judge. We compare the results of LLM-as-a-Judge
and Agent-as-a-Judge with Human-as-a-Judge. (I) represents performance on independent tasks, while (D) represents
performance considering task dependencies. Note:
 gray-box settings use carefully manually collected trajectory
data (which is nearly inaccessible in practical situations, see Appendix J). In contrast,
 black-box setting doesn’t
need to access to such data. The red scores represent the absolute judge shift compared with Human-as-a-Judge ( e.g.,
2.74%).
Metric MetaGPT (Hong et al., 2024b) GPT-Pilot (Pythagora.io, 2023) OpenHands (Wang et al., 2024d)
LLM-as-a-Judge
(a) Requirements Met (I) 19.39% (2.74%) 12.56% (32.24%) 11.47% (31.42%)
```

**[Chunk 5/6]** Page 1 | ID: `1-7` | Distance: 0.3727

```
in DevAI: MetaGPT (Hong et al., 2024b), GPT-Pilot (Pythagora.io, 2023), and OpenHands (Wang et al.,
2024d). We evaluate their performance using human judges (a painstaking process), LLM-as-a-Judge (Zheng
et al., 2024), and our Agent-as-a-Judge framework.
Through human evaluation, we found that GPT-Pilot and OpenHands were each able to satisfy about 29%
of the task requirements in DevAI, but only one full task—showing that DevAI presents a good level of
challenge to current systems. When comparing our human judges with our automatic Agent-as-a-Judge
framework, we found that Agent-as-a-Judge aligns more closely with the consensus of our human judges (90%)
as compared to LLM-as-a-Judge (70%) in all cases tested. In addition, we find that it aligns more closely
```

**[Chunk 6/6]** Page 9 | ID: `9-4` | Distance: 0.4229

```
4.3 Ablations For Agent-as-a-Judge
We conduct ablations to evaluate the impact of adding different components on Agent-as-a-Judge’s performance.
The components analyzed include ask, graph, read, locate, and retrieve. The component ablation study
for Agent-as-a-Judge reveals key insights into the performance gains from adding specific functionalities.
Table 4 Component Ablation Studies for Agent-as-a-Judge. We
analyze the impact of adding various components ( ask, graph,
read, locate, and retrieve) on the performance of Agent-as-a-
Judge for judging OpenHands.
Metric + ask + graph + read + locate + retrieve
Agent-as-a-Judge Performance
Alignment Rate 65.03% 75.95% 82.24% 90.44% 90.16%
With only the ask component, the agent
achieves a 65 .03% alignment rate. Adding
```

---

## Q: What alignment rate does Agent-as-a-Judge achieve using only the 'ask' component, and after adding 'graph,' 'read,' and 'locate'?
_Asked at 2026-09-20 19:34:06_

### Answer

Agent‑as‑a‑Judge attains an alignment rate of **65.03 %** when it uses only the **ask** component. Adding the **graph** component raises the rate to **75.95 %**, adding **read** further improves it to **82.24 %**, and incorporating **locate** boosts it to **90.44 %** (see Table 4 on page 9).

### Retrieved Chunks

**[Chunk 1/6]** Page 9 | ID: `9-4` | Distance: 0.2730

```
4.3 Ablations For Agent-as-a-Judge
We conduct ablations to evaluate the impact of adding different components on Agent-as-a-Judge’s performance.
The components analyzed include ask, graph, read, locate, and retrieve. The component ablation study
for Agent-as-a-Judge reveals key insights into the performance gains from adding specific functionalities.
Table 4 Component Ablation Studies for Agent-as-a-Judge. We
analyze the impact of adding various components ( ask, graph,
read, locate, and retrieve) on the performance of Agent-as-a-
Judge for judging OpenHands.
Metric + ask + graph + read + locate + retrieve
Agent-as-a-Judge Performance
Alignment Rate 65.03% 75.95% 82.24% 90.44% 90.16%
With only the ask component, the agent
achieves a 65 .03% alignment rate. Adding
```

**[Chunk 2/6]** Page 9 | ID: `9-5` | Distance: 0.2960

```
With only the ask component, the agent
achieves a 65 .03% alignment rate. Adding
the graph component increases performance
to 75.95%, as the agent can better understand
the relationships between files.
The introduction of read further improves
the alignment rate to 82 .24%, reflecting the
value of direct access to the contents of the
file. Incorporating locate brings a substantial boost to 90 .44%, as the agent can efficiently target files relevant
10
```

**[Chunk 3/6]** Page 9 | ID: `9-2` | Distance: 0.3348

```
black-box setting.
Figure 7 PR Curves comparing judge Methods.
Alignment Rate The Alignment Rate reflects how
closely the AI Judges’ evaluations align with human
consensus across all 365 requirements. It is defined
as the percentage of requirement evaluations that
are the same as the Human-as-a-Judge consensus
evaluation. Compared to LLM-as-a-Judge, Agent-
as-a-Judge consistently achieves a higher Alignment
Rate, closely matching human judgments. For
example, when evaluating OpenHands, Agent-as-a-
Judge reaches 92.07% and 90.44%, surpassing LLM-
as-a-Judge’s 70.76% and 60 .38% in both gray-box
and black-box settings. This shows that Agent-as-a-
Judge produces more accurate and human-aligned
evaluations, especially in complex scenarios.
PR Curves Judging developer agents is a class-
```

**[Chunk 4/6]** Page 38 | ID: `38-0` | Distance: 0.3384

```
K Ablations of Agent-as-a-Judge
K.1 Component Abalations
Table 5 Component Ablation Studies for Agent-as-a-Judge. We analyze the impact of sequentially adding various
components (ask, graph, read, locate, retrieve, planning, memory, and search) on the performance of Agent-as-a-
Judge for judging OpenHands.
Metric + ask + graph + read + locate + search + retrieve + planning + memory
Agent-as-a-Judge Performance
Alignment Rate 65.03% 75.95% 82.24% 90.44% 86.06% 90.16% 88.52% 87.97%
Analysis We designed 8 modular components for the Agent-as-a-Judge system. In the Table 5, components
are added progressively from left to right. If the addition of a component led to a significant performance drop,
```

**[Chunk 5/6]** Page 9 | ID: `9-1` | Distance: 0.3415

```
Judge Shift Judge Shift measures deviation from the Human-as-a-Judge consensus results, with lower values
indicating a closer alignment. As shown in table 3, Agent-as-a-Judge consistently outperforms LLM-as-a-Judge
across tasks, particularly those with task dependencies. For example, in Requirement (I), Agent-as-a-Judge
shows a Judge Shift as low as 0 .27%, while LLM-as-a-Judge reaches 31 .24% for OpenHands. This underscores
Agent-as-a-Judge’s stability and suitability for meeting task requirements. Furthermore, in the gray-box
setting, both Agent-as-a-Judge and LLM-as-a-Judge show even better results than their performance in the
black-box setting.
Figure 7 PR Curves comparing judge Methods.
Alignment Rate The Alignment Rate reflects how
```

**[Chunk 6/6]** Page 9 | ID: `9-3` | Distance: 0.3825

```
evaluations, especially in complex scenarios.
PR Curves Judging developer agents is a class-
imbalanced task, where meeting requirements is
much rarer than failing. Metrics like judge shift
and alignment rate can be misleading. For example,
since MetaGPT rarely meets requirements, LLM-as-a-Judge easily identifies most cases as negative (achieving
84.15% in the black-box setting). PR Curves offer a clearer performance measure by balancing precision and
recall. Agent-as-a-Judge even outperforms any single human evaluator on OpenHands and aligns closest with
majority voting. This shows that, in some cases, Agent-as-a-Judge can nearly replace human evaluators.
4.3 Ablations For Agent-as-a-Judge
```

---

## Q: Which search algorithm (BM2.5, Sentence-BERT, Fuzzy Search, or no search module) gave the best alignment rate?
_Asked at 2026-09-20 19:34:18_

### Answer

The highest alignment rate was achieved when **no search module was used** (the “without Search Module” configuration), which attained an alignment rate of **90.44 %**. This outperformed BM2.5 (86.06 %), Sentence‑BERT (87.70 %), and Fuzzy Search (85.52 %)【Passage 1 | Page 38】.

### Retrieved Chunks

**[Chunk 1/6]** Page 38 | ID: `38-4` | Distance: 0.2718

```
We initially hypothesized that the performance drop was due to the low precision of the search component,
particularly with BM2.5. To explore this, we replaced BM2.5 with Sentence-BERT (Reimers, 2019) as a more
advanced alternative and tested Fuzzy Search (Levenshtein, 1966) as a less precise option. However, neither
improved the performance of the Agent-as-a-Judge.
Table 6 Comparisons on Search module
with different engines.
Search Method Alignment Rate
BM2.5 86.06%
Sentence-BERT 87.70%
Fuzzy Search 85.52%
without Search Module 90.44%
hese results suggest that the performance issue is not due to BM2.5’s
poor search accuracy. Instead, the workspaces generated in our
DevAI tasks are too simple for the search component to have
```

**[Chunk 2/6]** Page 38 | ID: `38-5` | Distance: 0.4009

```
DevAI tasks are too simple for the search component to have
a significant impact. In simpler workspaces, direct retrieval and
evaluation are sufficient. Even though Sentence-BERT performed
better than the other methods, its alignment rate (87.70%) still falls
short of the configuration without the search component (90.44%).
As workspace complexity increases, the search component may
become more valuable.
39
```

**[Chunk 3/6]** Page 39 | ID: `39-0` | Distance: 0.5671

```
K.3 Search Algorithms in Retrieve Module
In our experiments, we found that accurately locating relevant information within a trajectory is a challenging
task. Although the addition of the retrieve component (gray-box) did not lead to a significant improvement
in performance in this specific case, its impact has been notable in other settings, such as in GPT-Pilot. As
shown in Table 3, the integration of retrieve in GPT-Pilot brought substantial gains.
Table 7 Ablations on retrieve.
Method Alignment Rate
Without retrieve 83.88%
With retrieve (gray-box) 86.61%
Trajectory Truncate (head) 86.61%
Trajectory Truncate (middle) 85.52%
Trajectory Truncate (tail) 82.51%
Step Truncate (head) 86.34%
Step Truncate (middle) 86.61%
Step Truncate (tail) 83.88%
```

**[Chunk 4/6]** Page 38 | ID: `38-1` | Distance: 0.5786

```
are added progressively from left to right. If the addition of a component led to a significant performance drop,
we removed it from further iterations. Our experiments showed that adding the components ask, graph, read,
and locate resulted in significant performance gains. However, when the search component was introduced,
there was a noticeable decline in performance.
We hypothesize that the performance drop from search is due to its role in retrieving relevant code snippets
(top-3) using BM25. The retrieval accuracy of BM25 (Robertson et al., 2009) might not have been high
enough, potentially introducing noise. Moreover, as noted in Table 1, the DevAI tasks in our experiments
did not generate a large amount of code. In fact, even when all code was fed into an LLM, the total content
```

**[Chunk 5/6]** Page 9 | ID: `9-5` | Distance: 0.5833

```
With only the ask component, the agent
achieves a 65 .03% alignment rate. Adding
the graph component increases performance
to 75.95%, as the agent can better understand
the relationships between files.
The introduction of read further improves
the alignment rate to 82 .24%, reflecting the
value of direct access to the contents of the
file. Incorporating locate brings a substantial boost to 90 .44%, as the agent can efficiently target files relevant
10
```

**[Chunk 6/6]** Page 14 | ID: `14-5` | Distance: 0.6058

```
2024b.
Bo Qiao, Liqun Li, Xu Zhang, Shilin He, Yu Kang, Chaoyun Zhang, Fangkai Yang, Hang Dong, Jue Zhang, Lu Wang,
et al. Taskweaver: A code-first agent framework. arXiv preprint arXiv:2311.17541 , 2023.
Vyas Raina, Adian Liusie, and Mark Gales. Is llm-as-a-judge robust? investigating universal adversarial attacks on
zero-shot llm assessment. arXiv preprint arXiv:2402.14016 , 2024.
N Reimers. Sentence-bert: Sentence embeddings using siamese bert-networks. arXiv preprint arXiv:1908.10084 , 2019.
Stephen Robertson, Hugo Zaragoza, et al. The probabilistic relevance framework: Bm25 and beyond. Foundations and
Trends® in Information Retrieval , 3(4):333–389, 2009.
Lin Shi, Weicheng Ma, and Soroush Vosoughi. Judging the judges: A systematic investigation of position bias in
```

---

## Q: Which two model architectures are mentioned most frequently in the DevAI user queries?
_Asked at 2026-09-20 19:34:27_

### Answer

The two model architectures that appear most often in the DevAI user queries are **SVM classifiers** and **LSTM models** (as noted on page 3, Passage 2).

### Retrieved Chunks

**[Chunk 1/4]** Page 3 | ID: `3-2` | Distance: 0.5019

```
DevAI is structured so that an agentic system starts by receiving a user query to begin development. The
system is then evaluated on how well it meets the requirements, with preferences serving as optional, softer
criteria. An example of one of the DevAI tasks can be seen in Figure 3.
The tasks in DevAI are relatively small-scale but cover commonly used key development techniques. As shown
in Figure 2, our tasks are tagged and cover a variety of key areas in AI: supervised learning, reinforcement
learning, computer vision, natural language processing, generative models, and others. Each of the tasks
is a real-world problem that could be given to a research engineer, while simultaneously being relatively
```

**[Chunk 2/4]** Page 3 | ID: `3-1` | Distance: 0.5116

```
here reflects the fact that it dominates many machine learning applications. (4) SVM classifiers (Cortes, 1995) and
LSTM models (Hochreiter, 1997) are two of the most widely used architectures—a fact reflected by DevAI.
2.2 The DevAI Dataset
Motivated by the ideas outlined above, we propose the DevAI dataset. DevAI consists of a curated set of 55
tasks, each defined by (1) a plain text user query that describes an AI development task; (2) a set of plain
text requirements (for a total of 365 requirements), each with a set of dependencies connecting them to other
requirements; and (3) a set of preferences (for a total of 125 preferences) which represent softer requirements.
DevAI is structured so that an agentic system starts by receiving a user query to begin development. The
```

**[Chunk 3/4]** Page 4 | ID: `4-2` | Distance: 0.5545

```
n.ai/blog/introducing-devin. As this example shows, task requirements in DevAI are structured as a Directed
Acyclic Graph (DAG), with nodes representing individual requirements and directed edges showing dependencies.
More examples are in Appendix G.
will refer to as “ AI developers ”): MetaGPT (Hong et al., 2024b), GPT-Pilot (Pythagora.io, 2023), and
OpenHands (Wang et al., 2024d)—all selected for their strong community acceptance (each having over 30,000
stars on GitHub).
Experiment Setup All of these three systems require a language model as a back-end engine, for which
we use gpt-4o-2024-05-13, a state-of-the-art language model. These AI developers were given a time-limit
of 1800 seconds to solve each task and were forcefully halted if they exceeded this time limit (we imposed
```

**[Chunk 4/4]** Page 10 | ID: `10-2` | Distance: 0.5573

```
applied to directly imitate software companies (Hong et al., 2024b; Qian et al., 2024a), debug code (Yang
et al., 2024a), run data science methods (Guo et al., 2024; Hong et al., 2024a; Li et al., 2024; Qiao et al.,
2023), and even write academic papers (Lu et al., 2024a).
Benchmarks for AI developments Benchmarks like MLAgentBench (Huang et al., 2024), ML-Bench (Liu
et al., 2023d), SUPER (Bogin et al., 2024), DS-bench (Jing et al., 2024), and MLE-Bench (Chan et al., 2024)
all focus on benchmarking agentic systems using AI tasks. However, DevAI distinguishes itself from all of
these by focusing on realistic user queries that target a complete development cycle. It further includes
a more comprehensive evaluation with multiple hierarchical requirements and preferences for each task.
```

---

## Q: What is requirement R1 in the 'Devin AI Software Engineer Plants Secret Messages in Images' task?
_Asked at 2026-09-20 19:34:36_

### Answer

Requirement **R1** states: *“Ensure the generated images are of 1080p resolution and saved in results/.”*【Page 4, Passage 1】.

### Retrieved Chunks

**[Chunk 1/4]** Page 4 | ID: `4-0` | Distance: 0.4311

```
Task 51: Devin AI Software Engineer Plants Secret Messages in Images
Query
Hi! Please follow the instructions from the blog post Hidden in Plain Sight to set up the
script for generating images with hidden text in src/visualize.py. Ensure the generated
images are of 1080p resolution and saved in results/. Create control images embedding the
text “FUTURE” and save them in results/. Please manually verify that the hidden text is
embedded in the images.
Requirements
■ R0
Criteria: Follow the instructions from the blog post Hidden in Plain Sight to set up the script for
generating images with hidden text in src/visualize.py.
Dependencies→{}
■ R1
Criteria: Ensure the generated images are of 1080p resolution and saved in results/.
Dependencies→{ R0}
■ R2
```

**[Chunk 2/4]** Page 4 | ID: `4-1` | Distance: 0.4590

```
■ R1
Criteria: Ensure the generated images are of 1080p resolution and saved in results/.
Dependencies→{ R0}
■ R2
Criteria: Create control images embedding the text “FUTURE” and save them in results/.
Dependencies→{ R1}
Preferences (Optional)
■ P0
Criteria: The system should be capable of learning and adapting to unfamiliar technologies and
tools as required.
■ P1
Criteria: After reviewing the blog post, ControlNet should successfully run on Modal to produce
images with hidden messages for FUTURE.
Figure 3 A task example in DevAI . This task is adapted from a real-world demo given at https://www.cognitio
n.ai/blog/introducing-devin. As this example shows, task requirements in DevAI are structured as a Directed
```

**[Chunk 3/4]** Page 30 | ID: `30-1` | Distance: 0.5584

```
Requirements:
Marking a requirement as satisfied must be made for this specific requirement disregarding the dependency
list. If a file (code, image, snapshot) is there but is empty or without any meaningful content - mark as
No.
1. Code:
The functionality must be in a file with the requested path.
The real data is replaced by simple synthetic - not satisfied.
2. Visualization/Reports:
The contents must be there and make sense even if not perfect from the ML/DS point of view.
3. Snapshots:
If a binary snapshot is not empty, mark as Yes.
Evaluator 38bb
EXECUTED SUCCESSFULLY: Yes [ ] / No [ ]
An output is marked yes if none of the following is satisfied.
1. The time spent is close to the time limit.
2. The last environmental message includes an error.
```

**[Chunk 4/4]** Page 1 | ID: `1-1` | Distance: 0.5940

```
Time: 1800.6 s
Cost: $1.7
Requirements:
Satisfied 0/2 (0%)
Hi!Pleasefollowtheinstructionandsetupthescriptfromthe
bloghttps://www.factsmachine.ai/p/hidden-in-
plain-sighttogenerate1080pimageswithhiddentext
(“FUTURE,”insrc/visualize.py.Savethemin
results/andverifythetextisembedded.
Time: 500.7s
Cost:$1.5
Requirements:
Satisfied 2/2 (100%)
1# src/visualize.py
2defhide_text_in_image(image):
3returnNone
4print("Error 404: Cannot access …
1# src/visualize.py
...
120sd=StableDiffusion()
121images=sd.run_inference.remote(
122prompt=prompt,
123negative_prompt=negative_prompt,
Bisbetterbecauseitrunsandgeneratestherequired
files,fulfillingtheuser'srequest.Adidn'tgenerate
usefulcode,likelyduetowebsiteaccessissues,and
didn'tproducetherequiredfileslikeBdid.
Interact
Agent A Agent B
EnvironmentWorkspace
```

---

## Q: Which of the three human evaluators (231a, 38bb, cn9o) made the most errors when judging GPT-Pilot, and what was the error rate?
_Asked at 2026-09-20 19:34:47_

### Answer

The evaluator **cn9o** made the most mistakes on GPT‑Pilot, with an error rate of **approximately 23.77 %** for that system (as reported in the paper).【Page 7, Passage 1】

### Retrieved Chunks

**[Chunk 1/6]** Page 7 | ID: `7-0` | Distance: 0.3340

```
While the consensus evaluation may not represent the absolute ground truth (we acknowledge that some
quantity of error likely would still exist even after this procedure), we expect the consensus evaluation to more
accurately approximate any extant ground truth (Clemen, 1989). If this holds, the majority vote should align
more closely with the consensus than with any individual evaluation. As shown in Figure 5, this is the case.
As seen in the results, although significant errors occur among all evaluators, the majority vote effectively
corrects most of these errors. Notably, cn9o made the most errors (for example, 23 .77% in evaluating
GPT-Pilot). After applying the majority vote from all three evaluators, the overall error rate dropped to
```

**[Chunk 2/6]** Page 6 | ID: `6-1` | Distance: 0.4214

```
evaluation and their self-reported post-hoc descriptions of how they resolved ambiguities are reported in
Figure 12 in Appendix H.
After the initial round of human evaluations (which totaled an estimated total of 58 human hours), we asked
our evaluators to discuss and reach a consensus on their assessments (which took an estimated total of 28 .5
additional human hours). This consensus, achieved after long sessions of debate, was used as the final human
evaluation result for each method.
Performance Analysis The results of this experiment are shown in Table 2. We found that the two best-
performing methods (GPT-Pilot and OpenHands) could satisfy about 29% of the requirements (or around
```

**[Chunk 3/6]** Page 7 | ID: `7-1` | Distance: 0.4949

```
GPT-Pilot). After applying the majority vote from all three evaluators, the overall error rate dropped to
6.01%, demonstrating the inherent benefits of majority voting.
Figure 5 Mismatch between the individual evalu-
ations and the consensus evaluation. In particular,
the majority vote classifier showed the smallest devi-
ation from the consensus evaluation.
Conclusion Human judgment errors are inevitable. To
reduce them, we suggest two methods. First, like in
this work, introduce a debate round after each judgment,
where individuals present evidence and either persuade
others or adjust their own opinions after discussion. This
is particularly important when there are only a few evalu-
ators, as majority voting with a small group can still lead
```

**[Chunk 4/6]** Page 6 | ID: `6-2` | Distance: 0.4984

```
performing methods (GPT-Pilot and OpenHands) could satisfy about 29% of the requirements (or around
44% if prerequisites are ignored) but only on one task could they meet all the requirements. This highlights
that DevAI offers a considerable but appropriate level of challenge for current and future methods. Moreover,
the fulfillment of intermediate requirements aligns with our expectations, as discussed in Section 2, that
DevAI provides richer feedback by uncovering how agentic systems falter during the process instead of just
focusing on a single performance metric at the end.
3.2 Judging Human-as-a-Judge
Figure 4 Between the three human evaluators, a large amount of disagreement was observed in their individual
```

**[Chunk 5/6]** Page 29 | ID: `29-1` | Distance: 0.5104

```
post-hoc evaluation criteria are shown in Figure 12.
Second round In the second round, the evaluators present and discuss their reasons for disagreeing with
judges. In doing so, human errors are likely corrected by their peers. Discussion among evaluators also helps
reduce human bias by examining each other’s thought processes thoroughly. Furthermore, the consensed
results are considered trustworthy given the assumption that it is unlikely that all three evaluators are
convinced by the same mistake or the same cognitive bias. The three evaluators took 9.5 hours together for
this second round of evaluation.
30
```

**[Chunk 6/6]** Page 5 | ID: `5-4` | Distance: 0.5378

```
Table 2 Human-as-a-Judge for AI Developers. (I) and (D) represent independent performance versus performance
considering task dependencies.
 indicates multiple experts evolved, and
 means the evaluations use white-box
testing (allowing access to the generated workspace, human-collected trajectories, and open-source codebases). The
results were derived from expert judgments and deliberations (see Appendix H).
Metric MetaGPT (Hong et al., 2024b) GPT-Pilot (Pythagora.io, 2023) OpenHands (Wang et al., 2024d)
/
 Human-as-a-Judge
(A) Requirements Met (I) 22.13% 44.80% 42.89%
(B) Requirements Met (D) 6.55% 28.96% 28.68%
(C) Self-Termination 41.81% 5.45% 54.54%
(D) Task Solve Rate 0.00% 1.81% 1.81%
6
```

---

## Q: In the diagram comparing LLM-as-a-Judge, Agent-as-a-Judge, and Human-as-a-Judge, what key drawback is highlighted for Human-as-a-Judge?
_Asked at 2026-09-20 19:34:56_

### Answer

The diagram points out that **Human‑as‑a‑Judge is less consistent and aligns poorly with the consensus** – its evaluations are more variable and have a lower alignment rate than the AI judges. In the paper it is noted that the Agent‑as‑a‑Judge “aligns more closely … than the individual human evaluators do” (Passage 1, p. 1) and that the human judges achieve a lower Alignment Rate compared with the AI judges (Passage 4, p. 9). This lower alignment is presented as the key drawback of Human‑as‑a‑Judge.

### Retrieved Chunks

**[Chunk 1/4]** Page 1 | ID: `1-8` | Distance: 0.3224

```
as compared to LLM-as-a-Judge (70%) in all cases tested. In addition, we find that it aligns more closely
with this ensemble than the individual human evaluators do, suggesting that—not only is it suitable as a
replacement for a human evaluator—but it could in fact be more useful than an average lone human evaluator.
2
```

**[Chunk 2/4]** Page 9 | ID: `9-1` | Distance: 0.3399

```
Judge Shift Judge Shift measures deviation from the Human-as-a-Judge consensus results, with lower values
indicating a closer alignment. As shown in table 3, Agent-as-a-Judge consistently outperforms LLM-as-a-Judge
across tasks, particularly those with task dependencies. For example, in Requirement (I), Agent-as-a-Judge
shows a Judge Shift as low as 0 .27%, while LLM-as-a-Judge reaches 31 .24% for OpenHands. This underscores
Agent-as-a-Judge’s stability and suitability for meeting task requirements. Furthermore, in the gray-box
setting, both Agent-as-a-Judge and LLM-as-a-Judge show even better results than their performance in the
black-box setting.
Figure 7 PR Curves comparing judge Methods.
Alignment Rate The Alignment Rate reflects how
```

**[Chunk 3/4]** Page 9 | ID: `9-3` | Distance: 0.3483

```
evaluations, especially in complex scenarios.
PR Curves Judging developer agents is a class-
imbalanced task, where meeting requirements is
much rarer than failing. Metrics like judge shift
and alignment rate can be misleading. For example,
since MetaGPT rarely meets requirements, LLM-as-a-Judge easily identifies most cases as negative (achieving
84.15% in the black-box setting). PR Curves offer a clearer performance measure by balancing precision and
recall. Agent-as-a-Judge even outperforms any single human evaluator on OpenHands and aligns closest with
majority voting. This shows that, in some cases, Agent-as-a-Judge can nearly replace human evaluators.
4.3 Ablations For Agent-as-a-Judge
```

**[Chunk 4/4]** Page 9 | ID: `9-2` | Distance: 0.3668

```
black-box setting.
Figure 7 PR Curves comparing judge Methods.
Alignment Rate The Alignment Rate reflects how
closely the AI Judges’ evaluations align with human
consensus across all 365 requirements. It is defined
as the percentage of requirement evaluations that
are the same as the Human-as-a-Judge consensus
evaluation. Compared to LLM-as-a-Judge, Agent-
as-a-Judge consistently achieves a higher Alignment
Rate, closely matching human judgments. For
example, when evaluating OpenHands, Agent-as-a-
Judge reaches 92.07% and 90.44%, surpassing LLM-
as-a-Judge’s 70.76% and 60 .38% in both gray-box
and black-box settings. This shows that Agent-as-a-
Judge produces more accurate and human-aligned
evaluations, especially in complex scenarios.
PR Curves Judging developer agents is a class-
```

---

## Q: What is the DevAI dataset, and how many tasks, requirements, and preferences does it contain?
_Asked at 2026-09-20 20:18:50_

### Answer

The DevAI dataset is a curated collection of AI‑development tasks designed for evaluating agentic systems. It comprises **55 distinct tasks**, each accompanied by **365 plain‑text requirements** (organized as a directed‑acyclic graph) and **125 preferences** that capture softer, optional criteria【Passage 3 | Page 3】.

### Retrieved Chunks

**[Chunk 1/4]** Page 3 | ID: `3-2` | Distance: 0.3716

```
DevAI is structured so that an agentic system starts by receiving a user query to begin development. The
system is then evaluated on how well it meets the requirements, with preferences serving as optional, softer
criteria. An example of one of the DevAI tasks can be seen in Figure 3.
The tasks in DevAI are relatively small-scale but cover commonly used key development techniques. As shown
in Figure 2, our tasks are tagged and cover a variety of key areas in AI: supervised learning, reinforcement
learning, computer vision, natural language processing, generative models, and others. Each of the tasks
is a real-world problem that could be given to a research engineer, while simultaneously being relatively
```

**[Chunk 2/4]** Page 22 | ID: `22-5` | Distance: 0.3929

```
Manual refinements were necessary to ensure the accuracy and clarity of DevAI. We perform two rounds of
comprehensive review and edits on DevAI, each round being done by a different participant. During these
manual refinements, we focus on the logical consistency of our queries and requirements, the correctness and
ambiguity of the language, and the applicability of the content to the task domain. We identified a moderate
number of errors in our dataset during the review.
E.5 Analyse the dataset
We categorized each requirement based on its focus, whether it was related to the data set, the machine
learning method, visualization, metrics, HCI, or data processing. While this approach provides a useful
```

**[Chunk 3/4]** Page 3 | ID: `3-1` | Distance: 0.4010

```
here reflects the fact that it dominates many machine learning applications. (4) SVM classifiers (Cortes, 1995) and
LSTM models (Hochreiter, 1997) are two of the most widely used architectures—a fact reflected by DevAI.
2.2 The DevAI Dataset
Motivated by the ideas outlined above, we propose the DevAI dataset. DevAI consists of a curated set of 55
tasks, each defined by (1) a plain text user query that describes an AI development task; (2) a set of plain
text requirements (for a total of 365 requirements), each with a set of dependencies connecting them to other
requirements; and (3) a set of preferences (for a total of 125 preferences) which represent softer requirements.
DevAI is structured so that an agentic system starts by receiving a user query to begin development. The
```

**[Chunk 4/4]** Page 3 | ID: `3-3` | Distance: 0.4245

```
is a real-world problem that could be given to a research engineer, while simultaneously being relatively
inexpensive computationally to run so as to reduce the cost of evaluating a method on this benchmark. Details
of the sample collection and human labeling process for DevAI are provided in Appendix E.
The requirements belonging to each task represent a milestone in the comprehensive development process and
are arranged as a directed acyclic graph (similar to the work by He et al. (2021)), with requirements such
as visualizing results depending on correct data loading and modeling. This allows for more comprehensive
non-sparse feedback than a binary success metric. Furthermore, the inclusion of hierarchical requirements
```

---

## Q: What percentage of evaluation time and cost does Agent-as-a-Judge save compared to using three human experts?
_Asked at 2026-09-20 20:18:51_

### Answer

Agent‑as‑a‑Judge requires only **118.43 minutes**, which is **2.36 %** of the time taken by the three human experts (86.5 hours).  In terms of cost it incurs just **30.58 USD**, i.e., **2.29 %** of the human‑evaluation cost (≈ 1,297.50 USD).  Consequently, it saves roughly **97.6 % of the evaluation time** and **97.7 % of the cost** compared with using three human judges.  

*Source: Passage 1, Page 10.*

### Retrieved Chunks

**[Chunk 1/4]** Page 10 | ID: `10-0` | Distance: 0.2278

```
to the requirements. However, adding retrieve does not provide a significant benefit in this case. In contrast,
as shown in Table 3, the judgment of MetaGPT and GPT-Pilot indicates that retrieve is useful, as the
trajectory provides additional valuable information.
4.4 Cost Analysis
The Human-as-a-Judge took the three evaluators a self-reported total of 86 .5 hours. With a 15 USD minimum
wage (assuming this would buy a subject expert in AI), a full evaluation under DevAI would cost around
1297.50 USD. In comparison, Agent-as-a-Judge cost only 30 .58 USD in API calls and took only 118 .43
minutes—2.29% of the cost and 2 .36% of the time of Human-as-a-Judge. LLM-as-a-Judge was faster at 10 .99
```

**[Chunk 2/4]** Page 7 | ID: `7-2` | Distance: 0.2726

```
is particularly important when there are only a few evalu-
ators, as majority voting with a small group can still lead
to errors (around 5% compared to consensus evaluation,
as shown in Figure 5). The second approach involves
assembling a larger panel of experts (more is better when
their accuracy exceeds 50% (Grofman et al., 1983)), with
over 5 people recommended by Hastie and Kameda (2005);
Larrick and Soll (2006), and relying on a majority vote.
However, due to the high cost of engaging more experts
and the fact that this is not always feasible in practice,
we argue for the former.
4 Agent-as-a-Judge: Evaluating Agents with Agents
Human evaluation, while somewhat reliable, is time-consuming and requires substantial expertise. To address
```

**[Chunk 3/4]** Page 9 | ID: `9-3` | Distance: 0.2858

```
evaluations, especially in complex scenarios.
PR Curves Judging developer agents is a class-
imbalanced task, where meeting requirements is
much rarer than failing. Metrics like judge shift
and alignment rate can be misleading. For example,
since MetaGPT rarely meets requirements, LLM-as-a-Judge easily identifies most cases as negative (achieving
84.15% in the black-box setting). PR Curves offer a clearer performance measure by balancing precision and
recall. Agent-as-a-Judge even outperforms any single human evaluator on OpenHands and aligns closest with
majority voting. This shows that, in some cases, Agent-as-a-Judge can nearly replace human evaluators.
4.3 Ablations For Agent-as-a-Judge
```

**[Chunk 4/4]** Page 17 | ID: `17-1` | Distance: 0.3057

```
Description: In the first level of experiments, we select three popular open-source developer
agents: MetaGPT, GPT-Pilot, and OpenHands. These agents are evaluated on the DevAI tasks
to establish performance baselines.
■ Step 4: Conducting Human-as-a-Judge Evaluation
Description: We conduct a Human-as-a-Judge experiment, where three human experts assess
the performance of the developer agents on the same DevAI tasks.
■ Step 5: Human-as-a-Judge Analysis (Experiment Level 2)
Description: In the second level of experiments, we statistically analyze the results of Human-as-
a-Judge evaluations, focusing on the costs of human labor and potential biases, highlighting the
challenges of relying on human evaluation for complex tasks.
■ Step 6: Agent-as-a-Judge Implementation
```

---

## Q: According to Section 4.4 (Cost Analysis), how much did Agent-as-a-Judge cost and how long did it take, compared to Human-as-a-Judge?
_Asked at 2026-09-20 20:18:53_

### Answer

According to Section 4.4 (Cost Analysis), the Agent‑as‑a‑Judge evaluation cost **$30.58** in API calls and took **118.43 minutes** to run. This represents only **2.29 % of the monetary cost** and **2.36 % of the time** required by the Human‑as‑a‑Judge, which took **86.5 hours** and cost about **$1,297.50** (Page 10).

### Retrieved Chunks

**[Chunk 1/6]** Page 10 | ID: `10-0` | Distance: 0.2828

```
to the requirements. However, adding retrieve does not provide a significant benefit in this case. In contrast,
as shown in Table 3, the judgment of MetaGPT and GPT-Pilot indicates that retrieve is useful, as the
trajectory provides additional valuable information.
4.4 Cost Analysis
The Human-as-a-Judge took the three evaluators a self-reported total of 86 .5 hours. With a 15 USD minimum
wage (assuming this would buy a subject expert in AI), a full evaluation under DevAI would cost around
1297.50 USD. In comparison, Agent-as-a-Judge cost only 30 .58 USD in API calls and took only 118 .43
minutes—2.29% of the cost and 2 .36% of the time of Human-as-a-Judge. LLM-as-a-Judge was faster at 10 .99
```

**[Chunk 2/6]** Page 9 | ID: `9-3` | Distance: 0.4327

```
evaluations, especially in complex scenarios.
PR Curves Judging developer agents is a class-
imbalanced task, where meeting requirements is
much rarer than failing. Metrics like judge shift
and alignment rate can be misleading. For example,
since MetaGPT rarely meets requirements, LLM-as-a-Judge easily identifies most cases as negative (achieving
84.15% in the black-box setting). PR Curves offer a clearer performance measure by balancing precision and
recall. Agent-as-a-Judge even outperforms any single human evaluator on OpenHands and aligns closest with
majority voting. This shows that, in some cases, Agent-as-a-Judge can nearly replace human evaluators.
4.3 Ablations For Agent-as-a-Judge
```

**[Chunk 3/6]** Page 18 | ID: `18-1` | Distance: 0.4372

```
Level 2
⁄leafExperiment 2a: Error analysis of human evaluations (Section 3.2)
Level 3
⁄leafExperiment 3a: AI judge baselines (Section 4.2)
⁄leafExperiment 3b: Ablation studies for Agent-as-a-Judge (Section 4.3)
B.2 Judges and Subjects of Evaluation
The following table summarizes the judge and the subject being evaluated in each experiment:
Experiment Who is the Judge? Who is being Judged?
Section 2.3 Human Developer Agents
Section 3.1 Human Developer Agents
Section 3.2 Human Human
Section 4.2 (1) LLM-as-a-Judge (1) Developer Agents
(2) Agent-as-a-Judge (2) Developer Agents
(3) Human (3) LLM-as-a-Judge
(4) Human (4) Agent-as-a-Judge
Section 4.3 Human Agent-as-a-Judge
19
```

**[Chunk 4/6]** Page 17 | ID: `17-1` | Distance: 0.4445

```
Description: In the first level of experiments, we select three popular open-source developer
agents: MetaGPT, GPT-Pilot, and OpenHands. These agents are evaluated on the DevAI tasks
to establish performance baselines.
■ Step 4: Conducting Human-as-a-Judge Evaluation
Description: We conduct a Human-as-a-Judge experiment, where three human experts assess
the performance of the developer agents on the same DevAI tasks.
■ Step 5: Human-as-a-Judge Analysis (Experiment Level 2)
Description: In the second level of experiments, we statistically analyze the results of Human-as-
a-Judge evaluations, focusing on the costs of human labor and potential biases, highlighting the
challenges of relying on human evaluation for complex tasks.
■ Step 6: Agent-as-a-Judge Implementation
```

**[Chunk 5/6]** Page 0 | ID: `0-5` | Distance: 0.4520

```
a better evaluation with a human is prohibitively expensive. We instead propose that agentic systems should
be used to evaluate agentic systems. Inspired by LLM-as-a-Judge (Zheng et al., 2024; Fu et al., 2023; Chen
et al., 2024b), which uses LLMs to evaluate LLMs, we call this framework Agent-as-a-Judge, of which it is
1
arXiv:2410.10934v2  [cs.AI]  16 Oct 2024
```

**[Chunk 6/6]** Page 9 | ID: `9-1` | Distance: 0.4585

```
Judge Shift Judge Shift measures deviation from the Human-as-a-Judge consensus results, with lower values
indicating a closer alignment. As shown in table 3, Agent-as-a-Judge consistently outperforms LLM-as-a-Judge
across tasks, particularly those with task dependencies. For example, in Requirement (I), Agent-as-a-Judge
shows a Judge Shift as low as 0 .27%, while LLM-as-a-Judge reaches 31 .24% for OpenHands. This underscores
Agent-as-a-Judge’s stability and suitability for meeting task requirements. Furthermore, in the gray-box
setting, both Agent-as-a-Judge and LLM-as-a-Judge show even better results than their performance in the
black-box setting.
Figure 7 PR Curves comparing judge Methods.
Alignment Rate The Alignment Rate reflects how
```

---

## Q: Which three open-source agentic frameworks were benchmarked on DevAI?
_Asked at 2026-09-20 20:18:54_

### Answer

The three open‑source code‑generation agentic frameworks benchmarked on DevAI are **MetaGPT**, **GPT‑Pilot**, and **OpenHands**【Passage 2 | Page 1】.

### Retrieved Chunks

**[Chunk 1/4]** Page 2 | ID: `2-0` | Distance: 0.3581

```
In addition, considering the evaluation cost, Agent-as-a-Judge saves 97.72% of the time and 97.64% of the
cost compared to involving three human experts.
In summary, the principal contributions of this work are:
• We release the DevAI dataset, which consists of 55 comprehensive AI development tasks with accompanying
tags, individual hierarchical requirements, and individual preferences.
• We benchmark three top open-source code generation agentic frameworks in DevAI, providing a more
comprehensive analysis than previous evaluations of them.
• We introduce the general Agent-as-a-Judge concept, allowing agentic systems a fair and rich evaluation
without the traditional costs associated with human involvement.
```

**[Chunk 2/4]** Page 1 | ID: `1-6` | Distance: 0.3640

```
Equally concerning, recent work has begun to introduce mechanisms designed specifically for the individual
tasks in the SWE-Bench dataset, leading to a lack of real-world generalization and violating Goodhart’s law:
“When a measure becomes a target, it ceases to be a good measure” (Goodhart, 1976).
To address the aforementioned issues with the current benchmarks in code generation, we introduce DevAI:
the AI Developer Dataset, which contains 55 real-world comprehensive AI app development tasks created
by expert annotators. We apply three leading open-source code-generating agentic frameworks to the tasks
in DevAI: MetaGPT (Hong et al., 2024b), GPT-Pilot (Pythagora.io, 2023), and OpenHands (Wang et al.,
```

**[Chunk 3/4]** Page 10 | ID: `10-2` | Distance: 0.3726

```
applied to directly imitate software companies (Hong et al., 2024b; Qian et al., 2024a), debug code (Yang
et al., 2024a), run data science methods (Guo et al., 2024; Hong et al., 2024a; Li et al., 2024; Qiao et al.,
2023), and even write academic papers (Lu et al., 2024a).
Benchmarks for AI developments Benchmarks like MLAgentBench (Huang et al., 2024), ML-Bench (Liu
et al., 2023d), SUPER (Bogin et al., 2024), DS-bench (Jing et al., 2024), and MLE-Bench (Chan et al., 2024)
all focus on benchmarking agentic systems using AI tasks. However, DevAI distinguishes itself from all of
these by focusing on realistic user queries that target a complete development cycle. It further includes
a more comprehensive evaluation with multiple hierarchical requirements and preferences for each task.
```

**[Chunk 4/4]** Page 17 | ID: `17-0` | Distance: 0.3960

```
A Outline of this Paper
Paper: Agent-as-a-Judge: Evaluating Agents with Agents
Key Logic
■ Step 1: Concept Proposal
Description: We propose the Agent-as-a-Judge concept, an extension of the LLM-as-a-Judge
framework, aimed at evaluating agentic systems using other agentic systems.
■ Step 2: Dataset Creation
Description: To address the lack of suitable datasets for evaluating agentic systems in automated
AI development, we introduce DevAI, a new dataset consisting of 55 realistic AI code generation
tasks. This also serves as a testbed for the Agent-as-a-Judge proof-of-concept.
■ Step 3: Baseline Evaluation of Developer Agents (Experiment Level 1)
Description: In the first level of experiments, we select three popular open-source developer
```

---

## Q: What is the average cost and average time for OpenHands?
_Asked at 2026-09-20 20:18:55_

### Answer

OpenHands incurred an average cost of **$6.38** and took an average of **362.41 seconds** per task (Table 1)【Passage 3 | Page 5】.

### Retrieved Chunks

**[Chunk 1/6]** Page 4 | ID: `4-3` | Distance: 0.4875

```
of 1800 seconds to solve each task and were forcefully halted if they exceeded this time limit (we imposed
this constraint, which was visible to the AI developers, as detailed in Appendix I). We capture the outputs
generated during the automated development process, including code, files, and other artifacts. Additionally,
we record key decisions and actions made by the agentic systems through some custom instrumentation code,
resulting in a development trajectory for each of the agentic systems.
Analysis The basic statistics are shown in Table 1. MetaGPT is the most cost-efficient (1 .19 USD), while
OpenHands is the most expensive (6 .38 USD). In terms of development time, OpenHands completes tasks
5
```

**[Chunk 2/6]** Page 5 | ID: `5-1` | Distance: 0.5449

```
in an average of 362 .41s, while GPT-Pilot takes the longest at 1622 .38s. On average, a full evaluation on
DevAI with one of these three took around 210 .65 USD and 14 hours to perform. While running, GPT-Pilot
generates the most output tokens at 59707 tokens, whereas OpenHands processed the most at 1252482 tokens
while producing the fewest at 8457 tokens. This suggests that OpenHands’s internal communication is more
complicated but is more parsimonious in its decisions.
MetaGPT, while being the most cost-effective, generates fewer saved code files (0 .42), suggesting it may be
less inclined to save files. In contrast, GPT-Pilot generates the most saved files (3 .84), reflecting a more
```

**[Chunk 3/6]** Page 5 | ID: `5-0` | Distance: 0.6263

```
Table 1 Preliminary Statistics of AI Developers. We compare three leading open-source code agents using metrics
such as average cost, average time, and the average number of generated files.
Metric MetaGPT (Hong et al., 2024b) GPT-Pilot (Pythagora.io, 2023) OpenHands (Wang et al., 2024d)
Basic Statistics
Version Data Interpreter (Hong et al., 2024a) 0.2.13 CodeAct v1.9 (Wang et al., 2024c)
(1) Average Cost $1.19 $3.92 $6.38
(2) Average Time 775.29s 1622.38s 362.41s
(3) Average Input Tokens 152863 606707 1252482
(4) Average Output Tokens 28546 59707 8457
(5) Average Saved Code Files 0.42 3.84 2.53
(6) Average Saved Code Lines 11.15 273.33 96.56
(7) Average Saved Files 4.42 5.91 3.60
in an average of 362 .41s, while GPT-Pilot takes the longest at 1622 .38s. On average, a full evaluation on
```

**[Chunk 4/6]** Page 5 | ID: `5-2` | Distance: 0.6914

```
less inclined to save files. In contrast, GPT-Pilot generates the most saved files (3 .84), reflecting a more
prolific output. The difference in saved code lines, with GPT-Pilot saving 273 .33 lines versus MetaGPT’s
11.15, underscores GPT-Pilot’s extensive output. Meanwhile, OpenHands, despite handling larger inputs,
seems less focused on executing code to generate files, as evidenced by its lower file output (2 .53 saved files).
These statistics align with real user experiences (as discussed in Appendix F).
Evaluations Note that the results in Table 1 are not directly indicative of performance but provide valuable
insights into the practical utility of DevAI and the performance of AI developers. The generated workspaces
```

**[Chunk 5/6]** Page 6 | ID: `6-1` | Distance: 0.6929

```
evaluation and their self-reported post-hoc descriptions of how they resolved ambiguities are reported in
Figure 12 in Appendix H.
After the initial round of human evaluations (which totaled an estimated total of 58 human hours), we asked
our evaluators to discuss and reach a consensus on their assessments (which took an estimated total of 28 .5
additional human hours). This consensus, achieved after long sessions of debate, was used as the final human
evaluation result for each method.
Performance Analysis The results of this experiment are shown in Table 2. We found that the two best-
performing methods (GPT-Pilot and OpenHands) could satisfy about 29% of the requirements (or around
```

**[Chunk 6/6]** Page 10 | ID: `10-0` | Distance: 0.7230

```
to the requirements. However, adding retrieve does not provide a significant benefit in this case. In contrast,
as shown in Table 3, the judgment of MetaGPT and GPT-Pilot indicates that retrieve is useful, as the
trajectory provides additional valuable information.
4.4 Cost Analysis
The Human-as-a-Judge took the three evaluators a self-reported total of 86 .5 hours. With a 15 USD minimum
wage (assuming this would buy a subject expert in AI), a full evaluation under DevAI would cost around
1297.50 USD. In comparison, Agent-as-a-Judge cost only 30 .58 USD in API calls and took only 118 .43
minutes—2.29% of the cost and 2 .36% of the time of Human-as-a-Judge. LLM-as-a-Judge was faster at 10 .99
```

---

## Q: Which system is the most cost-efficient and which is the most expensive?
_Asked at 2026-09-20 20:18:57_

### Answer

The most cost‑efficient system is **MetaGPT** (average cost ≈ $1.19), while the most expensive system is **OpenHands** (average cost ≈ $6.38)【Page 5, Table 1】 and this is reiterated in the analysis discussion【Page 4】.

### Retrieved Chunks

**[Chunk 1/6]** Page 5 | ID: `5-1` | Distance: 0.6396

```
in an average of 362 .41s, while GPT-Pilot takes the longest at 1622 .38s. On average, a full evaluation on
DevAI with one of these three took around 210 .65 USD and 14 hours to perform. While running, GPT-Pilot
generates the most output tokens at 59707 tokens, whereas OpenHands processed the most at 1252482 tokens
while producing the fewest at 8457 tokens. This suggests that OpenHands’s internal communication is more
complicated but is more parsimonious in its decisions.
MetaGPT, while being the most cost-effective, generates fewer saved code files (0 .42), suggesting it may be
less inclined to save files. In contrast, GPT-Pilot generates the most saved files (3 .84), reflecting a more
```

**[Chunk 2/6]** Page 5 | ID: `5-0` | Distance: 0.7064

```
Table 1 Preliminary Statistics of AI Developers. We compare three leading open-source code agents using metrics
such as average cost, average time, and the average number of generated files.
Metric MetaGPT (Hong et al., 2024b) GPT-Pilot (Pythagora.io, 2023) OpenHands (Wang et al., 2024d)
Basic Statistics
Version Data Interpreter (Hong et al., 2024a) 0.2.13 CodeAct v1.9 (Wang et al., 2024c)
(1) Average Cost $1.19 $3.92 $6.38
(2) Average Time 775.29s 1622.38s 362.41s
(3) Average Input Tokens 152863 606707 1252482
(4) Average Output Tokens 28546 59707 8457
(5) Average Saved Code Files 0.42 3.84 2.53
(6) Average Saved Code Lines 11.15 273.33 96.56
(7) Average Saved Files 4.42 5.91 3.60
in an average of 362 .41s, while GPT-Pilot takes the longest at 1622 .38s. On average, a full evaluation on
```

**[Chunk 3/6]** Page 34 | ID: `34-1` | Distance: 0.7275

```
to display the d et ec ti on results . Finally , evaluate the model ' s
p e r f o r m a n c e , i nc lu di ng metrics such as mAP and i nf er en ce time , and save
the e v a l u a t i o n results to ` results / metrics / m o d e l _ p e r f o r m a n c e . txt`. The
system should properly manage the launch and t e r m i n a t i o n of the
S tr ea mli t a p p l i c a t i o n to prevent u n n e c e s s a r y resource usage .\ n \ nThis is
a task that requires you to write , execute , and save source code . You
have a hard time limit of 3 0 minutes to produce your p r o g r a m m a t i c
solution to the given task . This time limit includes ex ec ut io n time .
The quality of your solution will be judged based on what you left in
```

**[Chunk 4/6]** Page 38 | ID: `38-0` | Distance: 0.7459

```
K Ablations of Agent-as-a-Judge
K.1 Component Abalations
Table 5 Component Ablation Studies for Agent-as-a-Judge. We analyze the impact of sequentially adding various
components (ask, graph, read, locate, retrieve, planning, memory, and search) on the performance of Agent-as-a-
Judge for judging OpenHands.
Metric + ask + graph + read + locate + search + retrieve + planning + memory
Agent-as-a-Judge Performance
Alignment Rate 65.03% 75.95% 82.24% 90.44% 86.06% 90.16% 88.52% 87.97%
Analysis We designed 8 modular components for the Agent-as-a-Judge system. In the Table 5, components
are added progressively from left to right. If the addition of a component led to a significant performance drop,
```

**[Chunk 5/6]** Page 4 | ID: `4-3` | Distance: 0.7463

```
of 1800 seconds to solve each task and were forcefully halted if they exceeded this time limit (we imposed
this constraint, which was visible to the AI developers, as detailed in Appendix I). We capture the outputs
generated during the automated development process, including code, files, and other artifacts. Additionally,
we record key decisions and actions made by the agentic systems through some custom instrumentation code,
resulting in a development trajectory for each of the agentic systems.
Analysis The basic statistics are shown in Table 1. MetaGPT is the most cost-efficient (1 .19 USD), while
OpenHands is the most expensive (6 .38 USD). In terms of development time, OpenHands completes tasks
5
```

**[Chunk 6/6]** Page 33 | ID: `33-1` | Distance: 0.7503

```
" o u t p u t _ t o k e n s " ,
" model " ,
" cost " ,
" l l m _ i n f e r e n c e _ t i m e " ,
" s t e p _ e x e c u t i o n _ t i m e "
]
} ,
" a c c u m u l a t e d _ u s a g e " : {
" type " : " object " ,
" p r o p e r t i e s " : {
" a c c u m u l a t e d _ c o s t " : {
" type " : " number " ,
" d e s c r i p t i o n " : " The total cost of the t r a j e c t o r y up to this step , in
USD . "
} ,
" a c c u m u l a t e d _ t i m e " : {
" type " : " number " ,
" d e s c r i p t i o n " : " The total time taken by the agent to complete the
t r a j e c t o r y up to this step , in seconds . "
}
} ,
" required " : [
" a c c u m u l a t e d _ c o s t " ,
" a c c u m u l a t e d _ t i m e "
]
}
} ,
```

---

## Q: What is the DevAI dataset, and how many tasks, requirements, and preferences does it contain?
_Asked at 2026-09-20 20:38:57_

### Answer

The DevAI dataset is a curated collection of AI‑development problems designed for evaluating agentic systems. It comprises **55 distinct tasks**; each task includes a set of **plain‑text requirements (totaling 365 requirements)** and a set of **softer “preferences” (totaling 125 preferences)**【Passage 3 | Page 3】.

### Retrieved Chunks

**[Chunk 1/4]** Page 3 | ID: `3-2` | Distance: 0.3716

```
DevAI is structured so that an agentic system starts by receiving a user query to begin development. The
system is then evaluated on how well it meets the requirements, with preferences serving as optional, softer
criteria. An example of one of the DevAI tasks can be seen in Figure 3.
The tasks in DevAI are relatively small-scale but cover commonly used key development techniques. As shown
in Figure 2, our tasks are tagged and cover a variety of key areas in AI: supervised learning, reinforcement
learning, computer vision, natural language processing, generative models, and others. Each of the tasks
is a real-world problem that could be given to a research engineer, while simultaneously being relatively
```

**[Chunk 2/4]** Page 22 | ID: `22-5` | Distance: 0.3929

```
Manual refinements were necessary to ensure the accuracy and clarity of DevAI. We perform two rounds of
comprehensive review and edits on DevAI, each round being done by a different participant. During these
manual refinements, we focus on the logical consistency of our queries and requirements, the correctness and
ambiguity of the language, and the applicability of the content to the task domain. We identified a moderate
number of errors in our dataset during the review.
E.5 Analyse the dataset
We categorized each requirement based on its focus, whether it was related to the data set, the machine
learning method, visualization, metrics, HCI, or data processing. While this approach provides a useful
```

**[Chunk 3/4]** Page 3 | ID: `3-1` | Distance: 0.4010

```
here reflects the fact that it dominates many machine learning applications. (4) SVM classifiers (Cortes, 1995) and
LSTM models (Hochreiter, 1997) are two of the most widely used architectures—a fact reflected by DevAI.
2.2 The DevAI Dataset
Motivated by the ideas outlined above, we propose the DevAI dataset. DevAI consists of a curated set of 55
tasks, each defined by (1) a plain text user query that describes an AI development task; (2) a set of plain
text requirements (for a total of 365 requirements), each with a set of dependencies connecting them to other
requirements; and (3) a set of preferences (for a total of 125 preferences) which represent softer requirements.
DevAI is structured so that an agentic system starts by receiving a user query to begin development. The
```

**[Chunk 4/4]** Page 3 | ID: `3-3` | Distance: 0.4245

```
is a real-world problem that could be given to a research engineer, while simultaneously being relatively
inexpensive computationally to run so as to reduce the cost of evaluating a method on this benchmark. Details
of the sample collection and human labeling process for DevAI are provided in Appendix E.
The requirements belonging to each task represent a milestone in the comprehensive development process and
are arranged as a directed acyclic graph (similar to the work by He et al. (2021)), with requirements such
as visualizing results depending on correct data loading and modeling. This allows for more comprehensive
non-sparse feedback than a binary success metric. Furthermore, the inclusion of hierarchical requirements
```

---

