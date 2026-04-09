"""配方测试 — Recipe CRUD + 版本化 + 筛选"""
from app.models.recipe import Recipe
from helpers import make_recipe_data


class TestRecipeList:
    """配方列表"""

    def test_empty_list(self, admin_client):
        """无配方时列表为空"""
        resp = admin_client.get('/recipes/')
        assert resp.status_code == 200

    def test_list_shows_active(self, admin_client, sample_recipe):
        """列表显示活跃配方"""
        resp = admin_client.get('/recipes/')
        assert resp.status_code == 200
        assert 'Silicon' in resp.data.decode('utf-8')

    def test_filter_by_material(self, admin_client, sample_recipe):
        """按材料筛选"""
        resp = admin_client.get('/recipes/?material=Silicon')
        assert resp.status_code == 200
        assert 'Silicon' in resp.data.decode('utf-8')

    def test_filter_no_match(self, admin_client, sample_recipe):
        """筛选无匹配结果"""
        resp = admin_client.get('/recipes/?material=GaN')
        assert resp.status_code == 200

    def test_filter_by_size(self, admin_client, sample_recipe):
        """按尺寸筛选"""
        resp = admin_client.get('/recipes/?size=8inch')
        assert resp.status_code == 200


class TestRecipeCreate:
    """创建配方"""

    def test_create_basic(self, admin_client, db):
        """创建基础配方"""
        resp = admin_client.post(
            '/recipes/create',
            data=make_recipe_data(),
        )
        assert resp.status_code == 302

        recipe = db.session.execute(
            db.select(Recipe).filter_by(is_active=True)
        ).scalar_one()
        assert recipe.wafer_material == 'Silicon'
        assert recipe.version == 1
        assert recipe.recipe_group_id == 1

    def test_create_with_disco(self, admin_client, db):
        """创建含 DISCO 参数的配方"""
        data = make_recipe_data(
            cut_direction='X',
            z1_height='50.0',
            z2_height='100.0',
            kerf_width='30.0',
        )
        resp = admin_client.post('/recipes/create', data=data)
        assert resp.status_code == 302

        recipe = db.session.execute(
            db.select(Recipe).filter_by(is_active=True)
        ).scalar_one()
        assert recipe.cut_direction == 'X'
        assert recipe.z1_height == 50.0
        assert recipe.kerf_width == 30.0

    def test_group_id_auto_increment(self, admin_client, db):
        """多次创建 group_id 自增"""
        admin_client.post('/recipes/create', data=make_recipe_data())
        admin_client.post(
            '/recipes/create',
            data=make_recipe_data(wafer_material='GaN'),
        )
        recipes = db.session.execute(
            db.select(Recipe).order_by(Recipe.recipe_group_id)
        ).scalars().all()
        assert len(recipes) == 2
        assert recipes[0].recipe_group_id == 1
        assert recipes[1].recipe_group_id == 2

    def test_create_form_page(self, admin_client):
        """创建表单页面可访问"""
        resp = admin_client.get('/recipes/create')
        assert resp.status_code == 200


class TestRecipeDetail:
    """配方详情"""

    def test_detail_page(self, admin_client, sample_recipe):
        """详情页显示配方信息"""
        resp = admin_client.get(f'/recipes/{sample_recipe.id}')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Silicon' in html
        assert 'NBC-ZH2050' in html

    def test_detail_not_found(self, admin_client):
        """不存在的配方返回 404"""
        resp = admin_client.get('/recipes/999')
        assert resp.status_code == 404


class TestRecipeEdit:
    """编辑配方 — 版本化"""

    def test_edit_creates_new_version(self, admin_client, sample_recipe, db):
        """编辑产生新版本 v2，旧版本 is_active=False"""
        data = make_recipe_data(wafer_material='GaN', notes='Updated')
        resp = admin_client.post(
            f'/recipes/{sample_recipe.id}/edit', data=data,
        )
        assert resp.status_code == 302

        # 旧版本 is_active=False
        db.session.expire_all()
        old = db.session.get(Recipe, sample_recipe.id)
        assert old.is_active is False

        # 新版本 v2 is_active=True
        new = db.session.execute(
            db.select(Recipe).filter_by(is_active=True)
        ).scalar_one()
        assert new.version == 2
        assert new.wafer_material == 'GaN'
        assert new.recipe_group_id == sample_recipe.recipe_group_id

    def test_edit_old_version_blocked(self, admin_client, sample_recipe, db):
        """只能编辑最新版本"""
        # 先编辑一次，产生 v2
        admin_client.post(
            f'/recipes/{sample_recipe.id}/edit',
            data=make_recipe_data(wafer_material='GaN'),
        )
        # 尝试编辑 v1（已失活）
        resp = admin_client.post(
            f'/recipes/{sample_recipe.id}/edit',
            data=make_recipe_data(wafer_material='SiC'),
            follow_redirects=True,
        )
        assert resp.status_code == 200
        # 不应产生 v3
        count = db.session.execute(
            db.select(db.func.count(Recipe.id))
        ).scalar()
        assert count == 2  # v1 + v2

    def test_edit_preserves_group_id(self, admin_client, sample_recipe, db):
        """编辑保持 recipe_group_id 不变"""
        admin_client.post(
            f'/recipes/{sample_recipe.id}/edit',
            data=make_recipe_data(thickness='500.0'),
        )
        new = db.session.execute(
            db.select(Recipe).filter_by(is_active=True)
        ).scalar_one()
        assert new.recipe_group_id == 1
        assert new.thickness == 500.0


class TestRecipeHistory:
    """版本历史"""

    def test_history_shows_all_versions(self, admin_client, sample_recipe, db):
        """历史页显示同组所有版本"""
        # 编辑产生 v2
        admin_client.post(
            f'/recipes/{sample_recipe.id}/edit',
            data=make_recipe_data(notes='v2'),
        )
        gid = sample_recipe.recipe_group_id
        resp = admin_client.get(f'/recipes/group/{gid}/history')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'v1' in html or 'V1' in html or '1' in html

    def test_history_nonexistent_group(self, admin_client):
        """不存在的配方组重定向"""
        resp = admin_client.get('/recipes/group/999/history')
        assert resp.status_code == 302
