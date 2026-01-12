# Backend package

# Default configuration
DEFAULT_CONFIG = {
    "filter_keywords": [
        "Vision-Language-Action Model",
        "VLA for Robotics",
        "Inference Efficiency",
        "Inference Efficiency",
        "Lightweight Architecture",
        "Inference Acceleration",
        "Edge Deployment",
    ],
    "negative_keywords": [
        "medical",
        "healthcare",
        "clinical",
        "protein",
        "molecule",
    ],
    "preset_questions": [
        "这篇论文的核心创新点是什么，他想解决什么问题，怎么解决的？",
        "请用一段话总结这篇论文，明确说明：论文试图解决的核心问题；提出的主要方法或框架；最终取得的主要效果或结论。要求语言简洁、信息密度高，不要复述摘要原文。",
        "这篇论文相对于已有工作有哪些明确的创新点？请逐条列出，并对每一条说明：相比以往方法改进或不同之处在哪里，以及该创新解决了什么具体问题或带来了什么优势。",
        "论文在实验或评估中最终实现了怎样的效果？请说明使用了哪些数据集和评价指标，与哪些基线方法进行了对比，以及在关键指标上的主要性能提升或结论。如果论文未给出明确的定量结果，也请说明原因。"
        # "基于他的前作，梳理这个方向的整个发展脉络，每一步相比于之前的工作都改进了什么，着重于几个不同的发展方向。",
        # "他的前作有哪些？使用表格仔细讲讲他的每篇前作，他和前作的区别是什么，主要改善是什么？着重于具体相比于之前文章的改动",
        # "论文提出了哪些关键技术方法，请列表格具体详细说明技术细节，需要包含具体的数学原理推导，以及具体参数。",
        # "他使用了哪些评价指标与数据集，列表格具体讲讲他的评价指标的细节与数据集的细节",
        # "论文在哪些数据集上进行了实验？主要的评估指标和性能提升是多少？",
        # "论文的主要局限性有哪些？未来可能的改进方向是什么？",
    ],
    "system_prompt": "你是一个专业的学术论文分析助手请用中文回答所有问题。先仔细阅读下面文章，分析文章的要点，回答要准确、简洁、有深度。使用 Markdown 格式，包括：标题（##）、要点列表（-）、代码块（```）、加粗（**）等，让回答更易读。重点关注论文的技术创新和实际价值。",
    "fetch_interval": 300,
    "max_papers_per_fetch": 1000,
    "model": "deepseek-chat",
    "temperature": 0.3,
    "max_tokens": 2000,
    "concurrent_papers": 10,
    "min_relevance_score_for_stage2": 6  # Minimum score to proceed to Stage 2 deep analysis
}
