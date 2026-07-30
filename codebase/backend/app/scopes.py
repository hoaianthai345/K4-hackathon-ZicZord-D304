from .schemas import CommunityUser, DiscordChannel, ScopeDescriptor
from .seed import CHANNELS, USERS


def user_record(user_id: str) -> CommunityUser | None:
    raw = next((item for item in USERS if item["id"] == user_id), None)
    return CommunityUser.model_validate(raw) if raw else None


def allowed_scope_keys(user: CommunityUser) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = {
        ("user", user.id),
        ("group", user.group_id),
        ("cohort", user.cohort_id),
    }
    if user.team_id:
        keys.add(("team", user.team_id))
    if user.lecture_room_id:
        keys.add(("room", user.lecture_room_id))
    if user.lab_room_id:
        keys.add(("room", user.lab_room_id))
    return keys


def scope_descriptors(user: CommunityUser) -> list[ScopeDescriptor]:
    values = [
        ScopeDescriptor(
            type="user",
            id=user.id,
            label=f"Chỉ mình {user.name.split()[-1]}",
            relation="Cá nhân",
        ),
    ]
    if user.team_id:
        values.append(
            ScopeDescriptor(
                type="team",
                id=user.team_id,
                label=f"Team {user.team_id}",
                relation="Project 4 người · 6 tuần",
            )
        )
    values.append(
        ScopeDescriptor(
            type="group",
            id=user.group_id,
            label=f"Group {user.group_id}",
            relation="Các team và mentor",
        )
    )
    if user.lecture_room_id:
        values.append(
            ScopeDescriptor(
                type="room",
                id=user.lecture_room_id,
                label=user.lecture_room_id.replace("LEC", "Lec"),
                relation="Phòng lý thuyết",
            )
        )
    if user.lab_room_id:
        values.append(
            ScopeDescriptor(
                type="room",
                id=user.lab_room_id,
                label=user.lab_room_id.replace("LAB", "Lab"),
                relation="Phòng thực hành",
            )
        )
    values.append(
        ScopeDescriptor(
            type="cohort",
            id=user.cohort_id,
            label=f"Cộng đồng {user.cohort_id}",
            relation="Chung · hỏi đáp · chia sẻ",
        )
    )
    return values


def visible_channels(user: CommunityUser) -> list[DiscordChannel]:
    allowed = allowed_scope_keys(user)
    return [
        DiscordChannel.model_validate(channel)
        for channel in CHANNELS
        if (channel["scope_type"], channel["scope_id"]) in allowed
    ]


def channel_record(channel_id: str) -> DiscordChannel | None:
    raw = next((item for item in CHANNELS if item["id"] == channel_id), None)
    return DiscordChannel.model_validate(raw) if raw else None


def can_access_channel(user: CommunityUser, channel: DiscordChannel) -> bool:
    return (channel.scope_type, channel.scope_id) in allowed_scope_keys(user)


def can_write_scope(user: CommunityUser, scope_type: str, scope_id: str) -> bool:
    if (scope_type, scope_id) not in allowed_scope_keys(user):
        return False
    if scope_type in {"group", "cohort", "room"}:
        return user.role == "mentor"
    return True
