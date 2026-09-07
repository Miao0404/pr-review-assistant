def chunk_pr_files(files: list[dict]) -> list[dict]:
    """
    把 PR 里每个文件的 diff 切成小块。
    每块保留文件名，方便后面知道这段代码来自哪里。
    """
    chunks = []

    for file in files:
        filename = file["filename"]
        patch = file["patch"]

        if not patch:
            continue

        # 按函数或者固定行数切块
        lines = patch.split("\n")
        current_chunk = []

        for line in lines:
            current_chunk.append(line)

            # 每 30 行切一块，避免单块太大
            if len(current_chunk) >= 30:
                chunks.append({
                    "filename": filename,
                    "content": "\n".join(current_chunk),
                })
                current_chunk = []

        # 剩余不足 30 行的也保留
        if current_chunk:
            chunks.append({
                "filename": filename,
                "content": "\n".join(current_chunk),
            })

    return chunks