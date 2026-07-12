from app.services.ai_gateway import parse_json_object, salvage_json_object


def test_parse_json_with_model_chatter_after_object():
    result = parse_json_object('先给出结果：{"answer":"可以继续追踪","source_indexes":[1]}\n以上是判断。')
    assert result["answer"] == "可以继续追踪"


def test_parse_json_with_think_block_and_trailing_comma():
    result = parse_json_object('<think>整理中</think>\n{"answer":"已完成","conclusions":["A"],}')
    assert result["conclusions"] == ["A"]


def test_parse_json_with_raw_newline_inside_string():
    result = parse_json_object('{"answer":"第一行\n第二行","source_indexes":[]}')
    assert result["answer"] == "第一行\n第二行"


def test_salvage_answer_when_json_envelope_is_malformed():
    result = salvage_json_object('{"answer":"只保留这个回答","conclusions":["A"],}')
    assert result["answer"] == "只保留这个回答"
    assert result["conclusions"] == ["A"]
