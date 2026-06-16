def match_keywords(keywords_str: str, search_results: list[dict]) -> dict | None:
    """
    对 keywords 拆词，在搜索结果中匹配。

    Args:
        keywords_str: 逗号分隔的关键词，如 "clip,claw,hair"
        search_results: 搜索结果列表 [{title, url, ...}, ...]

    Returns:
        第一个命中的商品 dict，无匹配返回 None
    """
    if not keywords_str or not search_results:
        return None

    # 拆分 keywords，去空白、去重、忽略空串
    target_keywords = list(
        dict.fromkeys(kw.strip().lower() for kw in keywords_str.split(",") if kw.strip())
    )

    for result in search_results:
        title = result.get("title", "").lower()
        for keyword in target_keywords:
            if keyword and keyword in title:
                return {**result, "matched_keyword": keyword}

    return None
