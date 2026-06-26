
from sqlalchemy import delete, insert, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.projection.mutations import (
    AppendMutation,
    DeleteMutation,
    IncrementMutation,
    InsertMutation,
    MergeMutation,
    ProjectionBatch,
    SetMutation,
    UpsertMutation,
)


class ProjectionExecutor:
    """
    Translates pure ProjectionMutations into SQL statements and executes them.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute_batch(self, batch: ProjectionBatch):
        for mutation in batch.mutations:
            await self._execute_mutation(mutation)

    async def _execute_mutation(self, mutation):
        if isinstance(mutation, IncrementMutation):
            await self._handle_increment(mutation)
        elif isinstance(mutation, SetMutation):
            await self._handle_set(mutation)
        elif isinstance(mutation, InsertMutation):
            await self._handle_insert(mutation)
        elif isinstance(mutation, DeleteMutation):
            await self._handle_delete(mutation)
        elif isinstance(mutation, AppendMutation):
            await self._handle_append(mutation)
        elif isinstance(mutation, MergeMutation):
            await self._handle_merge(mutation)
        elif isinstance(mutation, UpsertMutation):
            await self._handle_upsert(mutation)
        else:
            raise ValueError(f"Unknown mutation type {type(mutation)}")

    def _get_pk_col(self, model):
        return next(iter(model.__table__.primary_key.columns))

    def _get_lookup_col(self, model, target_id):
        pk_col = self._get_pk_col(model)
        if isinstance(target_id, str):
            for col in model.__table__.columns:
                if col.name.endswith("_id") and col.name != "id":
                    return col
        return pk_col

    async def _handle_increment(self, m: IncrementMutation):
        col = self._get_lookup_col(m.model, m.target_id)
        stmt = update(m.model).where(col == m.target_id).values(
            {m.field: getattr(m.model, m.field) + m.amount}
        )
        await self.session.execute(stmt)

    async def _handle_set(self, m: SetMutation):
        col = self._get_lookup_col(m.model, m.target_id)
        stmt = update(m.model).where(col == m.target_id).values(
            {m.field: m.value}
        )
        await self.session.execute(stmt)

    async def _handle_insert(self, m: InsertMutation):
        stmt = insert(m.model).values(**m.values)
        await self.session.execute(stmt)

    async def _handle_delete(self, m: DeleteMutation):
        col = self._get_lookup_col(m.model, m.target_id)
        stmt = delete(m.model).where(col == m.target_id)
        await self.session.execute(stmt)

    async def _handle_append(self, m: AppendMutation):
        # Specific to PostgreSQL JSONB
        from sqlalchemy import cast
        from sqlalchemy.dialects.postgresql import JSONB

        col = self._get_lookup_col(m.model, m.target_id)
        field_attr = getattr(m.model, m.field)
        stmt = update(m.model).where(col == m.target_id).values(
            {m.field: field_attr.op('||')(cast([m.item], JSONB))}
        )
        await self.session.execute(stmt)

    async def _handle_merge(self, m: MergeMutation):
        # Specific to PostgreSQL JSONB
        from sqlalchemy import cast
        from sqlalchemy.dialects.postgresql import JSONB

        col = self._get_lookup_col(m.model, m.target_id)
        field_attr = getattr(m.model, m.field)
        stmt = update(m.model).where(col == m.target_id).values(
            {m.field: field_attr.op('||')(cast(m.data, JSONB))}
        )
        await self.session.execute(stmt)

    async def _handle_upsert(self, m: UpsertMutation):
        # Using PostgreSQL specific insert... ON CONFLICT
        col = self._get_lookup_col(m.model, m.target_id)
        stmt = pg_insert(m.model).values(**m.values)

        # Determine the index elements for conflict
        # We assume `col` is unique/primary key for conflict target
        update_dict = {k: v for k, v in m.values.items() if k != col.name}
        if update_dict:
            stmt = stmt.on_conflict_do_update(
                index_elements=[col],
                set_=update_dict
            )
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=[col])

        await self.session.execute(stmt)
