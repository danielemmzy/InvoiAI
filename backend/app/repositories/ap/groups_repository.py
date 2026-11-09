from uuid import UUID
from app.repositories.base import BaseRepository
from app.mappers.ap.workflow_engine_mapper import ApprovalGroupMapper, ApprovalGroupMemberMapper
from app.models.domain.ap import ApprovalGroup

class ApprovalGroupRepository(BaseRepository):
    table_name = "ap_approval_groups"
    mapper = ApprovalGroupMapper

    async def list_groups(self, org_id: UUID):
        return self._many(self.table().select("*").eq("org_id", str(org_id)).order("name").execute())

    async def create_group(self, group: ApprovalGroup | dict):
        return await self.create(group)

    async def update_group(self, group_id: UUID, data):
        return await self.update(group_id, data)

    async def delete_group(self, group_id: UUID) -> bool:
        return await self.delete(group_id)

    async def get_group(self, group_id: UUID):
        return await self.get(group_id)


class ApprovalGroupMemberRepository(BaseRepository):
    table_name = "ap_approval_group_members"
    mapper = ApprovalGroupMemberMapper

    async def list_members(self, group_id: UUID):
        return self._many(self.table().select("*").eq("group_id", str(group_id)).execute())

    async def list_member_user_ids(self, group_id: UUID) -> list[str]:
        rows = self.raw_many(self.table().select("user_id").eq("group_id", str(group_id)).execute())
        return [r["user_id"] for r in rows]

    async def is_member(self, group_id: UUID, user_id: UUID) -> bool:
        response = self.table().select("id").eq("group_id", str(group_id)).eq("user_id", str(user_id)).limit(1).execute()
        return bool(response.data)

    async def add_member(self, group_id: UUID, user_id: UUID):
        return self.table().insert({"group_id": str(group_id), "user_id": str(user_id)}).execute()

    async def remove_member(self, group_id: UUID, user_id: UUID) -> bool:
        self.table().delete().eq("group_id", str(group_id)).eq("user_id", str(user_id)).execute()
        return True
