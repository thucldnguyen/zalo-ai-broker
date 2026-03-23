"""
Anthropic tool schemas, system prompts, and message builders for the
extraction and reply-generation calls.
"""

from typing import List, Optional

from core.models import LeadProfile, Message


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

EXTRACTION_SYSTEM_PROMPT = """\
Bạn là trợ lý phân tích tin nhắn bất động sản Việt Nam. \
Trích xuất thông tin có cấu trúc từ tin nhắn của khách hàng.

Quy tắc ngân sách:
- "2-3 tỷ" → budget_min=2000000000, budget_max=3000000000
- "2 tỷ" (một giá) → budget_min=1700000000, budget_max=2300000000 (±15%)
- "500 triệu" → budget_min=425000000, budget_max=575000000
- Không đề cập → để null

Mức độ quan tâm:
- "hot": dấu hiệu khẩn cấp (cần gấp, hôm nay, ngay, trong tuần, càng sớm càng tốt)
- "warm": đang tìm hiểu, hỏi thông tin, muốn xem, đặt câu hỏi
- "cold": không có dấu hiệu cụ thể

Ý định:
- "buy": mua để ở (mua, về ở, chuyển về)
- "invest": đầu tư, cho thuê, sinh lời
- "rent": cần thuê nhà
- "browse": không rõ ý định

Chỉ trích xuất thông tin thực sự có trong tin nhắn, không suy đoán thêm.\
"""

REPLY_SYSTEM_PROMPT = """\
Bạn là chuyên gia tư vấn bất động sản Việt Nam. \
Tạo tin nhắn thuyết phục, tự nhiên cho môi giới gửi cho khách hàng.

TUYỆT ĐỐI KHÔNG:
- Bịa đặt số liệu cụ thể (số căn còn lại, % lợi nhuận, số khách quan tâm) \
  nếu không có trong hồ sơ khách hàng
- Cam kết về pháp lý hoặc giấy tờ nếu không có thông tin xác thực
- Đưa ra tên dự án / mức giá cụ thể không có trong hồ sơ

YÊU CẦU:
- Tin nhắn tự nhiên, thân thiện như người Việt Nam thật sự
- Cá nhân hóa theo tên, ngân sách, khu vực của khách (nếu có)
- 50–150 từ mỗi tin nhắn
- Dùng "Em" (môi giới) và "Anh/Chị" (khách) theo phong cách Việt Nam\
"""


# ---------------------------------------------------------------------------
# Tool schemas (Anthropic tool_use format)
# ---------------------------------------------------------------------------

EXTRACTION_TOOL = {
    "name": "extract_lead_data",
    "description": "Trích xuất thông tin có cấu trúc từ tin nhắn bất động sản của khách hàng",
    "input_schema": {
        "type": "object",
        "properties": {
            "budget_min": {
                "type": ["integer", "null"],
                "description": "Ngân sách tối thiểu tính bằng VND (null nếu không đề cập)",
            },
            "budget_max": {
                "type": ["integer", "null"],
                "description": "Ngân sách tối đa tính bằng VND (null nếu không đề cập)",
            },
            "locations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Danh sách khu vực/quận quan tâm",
            },
            "interest_level": {
                "type": "string",
                "enum": ["hot", "warm", "cold"],
                "description": "Mức độ quan tâm của khách",
            },
            "intent": {
                "type": "string",
                "enum": ["buy", "invest", "rent", "browse"],
                "description": "Ý định của khách hàng",
            },
            "property_types": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["apartment", "villa", "land", "office"],
                },
                "description": "Loại bất động sản quan tâm",
            },
            "bedroom_count": {
                "type": ["integer", "null"],
                "description": "Số phòng ngủ yêu cầu (null nếu không đề cập)",
            },
            "key_phrases": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Các cụm từ quan trọng về yêu cầu/ưu tiên của khách",
            },
            "open_questions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Câu hỏi hoặc thắc mắc chưa được trả lời",
            },
        },
        "required": [
            "interest_level",
            "intent",
            "locations",
            "property_types",
            "key_phrases",
            "open_questions",
        ],
    },
}

REPLY_TOOL = {
    "name": "generate_reply_suggestions",
    "description": "Tạo danh sách gợi ý tin nhắn tiếng Việt cho môi giới bất động sản",
    "input_schema": {
        "type": "object",
        "properties": {
            "suggestions": {
                "type": "array",
                "description": "Danh sách gợi ý tin nhắn",
                "items": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Nội dung tin nhắn tiếng Việt",
                        },
                        "tactics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Chiến thuật sử dụng: urgency, scarcity, social_proof, "
                                "value_proposition, limited_time_offer, soft_touch, answer_question"
                            ),
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Lý do chọn chiến thuật này (tiếng Anh hoặc tiếng Việt)",
                        },
                    },
                    "required": ["message", "tactics", "reasoning"],
                },
            }
        },
        "required": ["suggestions"],
    },
}


# ---------------------------------------------------------------------------
# Message builders
# ---------------------------------------------------------------------------

def build_extraction_messages(
    text: str,
    history: List[Message],
    response_time_seconds: Optional[int] = None,
) -> list:
    """Build the Anthropic messages list for the extraction call."""
    parts: List[str] = []

    # Include last 5 messages as context (history is most-recent-first, so reverse)
    recent = list(reversed(history[:5]))
    if recent:
        lines = []
        for msg in recent:
            role = "Môi giới" if msg.is_broker else "Khách"
            lines.append(f"{role}: {msg.text}")
        parts.append("Lịch sử hội thoại gần đây:\n" + "\n".join(lines))

    if response_time_seconds is not None:
        parts.append(f"Thời gian phản hồi của khách: {response_time_seconds} giây")

    parts.append(f"Tin nhắn mới của khách: {text}")

    return [{"role": "user", "content": "\n\n".join(parts)}]


def build_reply_messages(
    profile: LeadProfile,
    approach: str,
    history: List[Message],
    tactics: List[str],
    count: int,
) -> list:
    """Build the Anthropic messages list for the reply-generation call."""
    lines: List[str] = ["Hồ sơ khách hàng:"]

    if profile.name:
        lines.append(f"- Tên: {profile.name}")
    if profile.budget_min and profile.budget_max:
        lines.append(
            f"- Ngân sách: {profile.budget_min / 1e9:.1f}–{profile.budget_max / 1e9:.1f} tỷ VND"
        )
    if profile.locations:
        lines.append(f"- Khu vực: {', '.join(profile.locations)}")
    if profile.property_types:
        lines.append(f"- Loại BĐS: {', '.join(profile.property_types)}")
    if profile.key_phrases:
        lines.append(f"- Yêu cầu: {', '.join(profile.key_phrases)}")
    lines.append(f"- Mức độ quan tâm: {profile.interest_level.value}")
    lines.append(f"- Ý định: {profile.intent.value}")
    lines.append(f"- Số lần tương tác: {profile.total_interactions}")

    # Conversation context (history is most-recent-first, reverse to chronological)
    recent = list(reversed(history[:6]))
    if recent:
        conv_lines = []
        for msg in recent:
            role = "Môi giới" if msg.is_broker else "Khách"
            conv_lines.append(f"{role}: {msg.text}")
        lines.append("\nLịch sử hội thoại gần đây:\n" + "\n".join(conv_lines))

    lines.append(f"\nChiến lược: {approach}")
    lines.append(f"Chiến thuật gợi ý: {', '.join(tactics)}")
    lines.append(f"\nTạo {count} gợi ý tin nhắn khác nhau phù hợp với chiến lược và hồ sơ khách hàng.")

    return [{"role": "user", "content": "\n".join(lines)}]
