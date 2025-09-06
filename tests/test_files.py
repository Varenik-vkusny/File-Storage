import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from backend import models
from backend.roles import FileVisibility


class TestGetFileAccess:
    """Тесты для эндпоинта GET /files/{file_id} (получение информации)."""

    @pytest.mark.anyio
    async def test_owner_can_see_private_file(
        self,
        authenticated_client_user: AsyncClient,
        test_user: models.User,
        db_session: AsyncSession,
    ):
        """Проверяет, что владелец может видеть свой приватный файл."""

        private_file = models.File(
            filename="private.pdf",
            s3_path=f"{uuid.uuid4()}.pdf",
            visibility=FileVisibility.PRIVATE,
            owner_id=test_user.id,
            department_id=test_user.department_id,
        )
        db_session.add(private_file)
        await db_session.commit()

        response = await authenticated_client_user.get(f"/files/{private_file.id}")
        assert response.status_code == 200
        assert response.json()["filename"] == "private.pdf"

    @pytest.mark.anyio
    async def test_admin_can_see_others_private_file(
        self,
        authenticated_client_admin: AsyncClient,
        test_user: models.User,
        db_session: AsyncSession,
    ):
        """Проверяет, что администратор может видеть чужой приватный файл."""

        private_file = models.File(
            filename="private.pdf",
            s3_path=f"{uuid.uuid4()}.pdf",
            visibility=FileVisibility.PRIVATE,
            owner_id=test_user.id,
            department_id=test_user.department_id,
        )
        db_session.add(private_file)
        await db_session.commit()

        response = await authenticated_client_admin.get(f"/files/{private_file.id}")
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_manager_cannot_see_private_file_of_other_department(
        self,
        authenticated_client_manager: AsyncClient,
        test_user: models.User,
        db_session: AsyncSession,
    ):
        """Проверяет, что менеджер (из отдела 2) НЕ может видеть приватный файл пользователя из другого отдела (отдел 1)."""

        private_file = models.File(
            filename="private.pdf",
            s3_path=f"{uuid.uuid4()}.pdf",
            visibility=FileVisibility.PRIVATE,
            owner_id=test_user.id,
            department_id=test_user.department_id,
        )
        db_session.add(private_file)
        await db_session.commit()

        response = await authenticated_client_manager.get(f"/files/{private_file.id}")
        assert response.status_code == 403
        assert response.json()["detail"] == "У вас нет доступа к этому файлу!"

    @pytest.mark.anyio
    async def test_another_user_cannot_see_private_file(
        self,
        authenticated_client_user: AsyncClient,
        test_another_user: models.User,
        db_session: AsyncSession,
    ):
        """
        Проверяет, что обычный пользователь (test_user) НЕ может видеть
        приватный файл другого пользователя (test_another_user), даже если они в одном отделе.
        """

        private_file = models.File(
            filename="another_user_private.pdf",
            s3_path=f"{uuid.uuid4()}.pdf",
            visibility=FileVisibility.PRIVATE,
            owner_id=test_another_user.id,
            department_id=test_another_user.department_id,
        )
        db_session.add(private_file)
        await db_session.commit()

        response = await authenticated_client_user.get(f"/files/{private_file.id}")

        assert response.status_code == 403


class TestDeleteFileAccess:
    """Тесты для эндпоинта DELETE /files/{file_id}."""

    @pytest.mark.anyio
    async def test_user_can_delete_own_file(
        self,
        authenticated_client_user: AsyncClient,
        test_user: models.User,
        db_session: AsyncSession,
    ):
        """Проверяет, что пользователь может удалить свой собственный файл."""

        user_file = models.File(
            filename="file.pdf",
            s3_path=f"{uuid.uuid4()}.pdf",
            visibility=FileVisibility.PRIVATE,
            owner_id=test_user.id,
            department_id=test_user.department_id,
        )
        db_session.add(user_file)
        await db_session.commit()

        response = await authenticated_client_user.delete(f"/files/{user_file.id}")
        assert response.status_code == 204

    @pytest.mark.anyio
    async def test_admin_can_delete_others_file(
        self,
        authenticated_client_admin: AsyncClient,
        test_user: models.User,
        db_session: AsyncSession,
    ):
        """Проверяет, что администратор может удалить чужой файл."""

        user_file = models.File(
            filename="file.pdf",
            s3_path=f"{uuid.uuid4()}.pdf",
            visibility=FileVisibility.PRIVATE,
            owner_id=test_user.id,
            department_id=test_user.department_id,
        )
        db_session.add(user_file)
        await db_session.commit()

        response = await authenticated_client_admin.delete(f"/files/{user_file.id}")
        assert response.status_code == 204

    @pytest.mark.anyio
    async def test_manager_cannot_delete_file_from_other_department(
        self,
        authenticated_client_manager: AsyncClient,
        test_user: models.User,
        db_session: AsyncSession,
    ):
        """Проверяет, что менеджер НЕ может удалить файл из чужого отдела."""

        user_file = models.File(
            filename="file.pdf",
            s3_path=f"{uuid.uuid4()}.pdf",
            visibility=FileVisibility.PRIVATE,
            owner_id=test_user.id,
            department_id=test_user.department_id,
        )
        db_session.add(user_file)
        await db_session.commit()

        response = await authenticated_client_manager.delete(f"/files/{user_file.id}")
        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "У вас недостаточно прав для удаления этого файла!"
        )

    @pytest.mark.anyio
    async def test_another_user_cannot_delete_others_file(
        self,
        authenticated_client_another_user: AsyncClient,
        test_user: models.User,
        db_session: AsyncSession,
    ):
        """Проверяет, что обычный пользователь НЕ может удалить чужой файл."""

        user_file = models.File(
            filename="file.pdf",
            s3_path=f"{uuid.uuid4()}.pdf",
            visibility=FileVisibility.PRIVATE,
            owner_id=test_user.id,
            department_id=test_user.department_id,
        )
        db_session.add(user_file)
        await db_session.commit()

        response = await authenticated_client_another_user.delete(
            f"/files/{user_file.id}"
        )
        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "У вас недостаточно прав для удаления этого файла!"
        )
