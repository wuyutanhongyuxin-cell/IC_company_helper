"""报告测试 — HTML 预览 + PDF 下载 (mock WeasyPrint)"""
import sys
from unittest.mock import MagicMock, patch


class TestHtmlPreview:
    """HTML 预览"""

    def test_preview_completed(self, admin_client, completed_order):
        """已完成工单预览正常"""
        resp = admin_client.get(
            f'/reports/delivery/{completed_order.id}/preview'
        )
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Completed Corp' in html

    def test_preview_has_inspection_data(self, admin_client, completed_order):
        """预览包含检验数据"""
        resp = admin_client.get(
            f'/reports/delivery/{completed_order.id}/preview'
        )
        html = resp.data.decode('utf-8')
        assert '95.5' in html

    def test_preview_non_completed_blocked(self, admin_client, sample_order):
        """未完成工单无法预览"""
        resp = admin_client.get(
            f'/reports/delivery/{sample_order.id}/preview'
        )
        assert resp.status_code == 400

    def test_preview_not_found(self, admin_client):
        """不存在的工单返回 404"""
        resp = admin_client.get('/reports/delivery/999/preview')
        assert resp.status_code == 404


class TestPdfDownload:
    """PDF 下载"""

    def test_pdf_with_mock(self, admin_client, completed_order):
        """Mock WeasyPrint 生成 PDF"""
        mock_weasyprint = MagicMock()
        mock_weasyprint.HTML.return_value.write_pdf.return_value = b'%PDF-mock'

        with patch.dict(sys.modules, {
            'weasyprint': mock_weasyprint,
            'weasyprint.text': mock_weasyprint.text,
            'weasyprint.text.fonts': mock_weasyprint.text.fonts,
        }):
            resp = admin_client.get(
                f'/reports/delivery/{completed_order.id}'
            )
        assert resp.status_code == 200
        assert resp.content_type == 'application/pdf'
        assert resp.data == b'%PDF-mock'
        # 文件名包含工单号
        disp = resp.headers.get('Content-Disposition', '')
        assert completed_order.order_number in disp

    def test_pdf_weasyprint_not_installed(self, admin_client, completed_order):
        """WeasyPrint 未安装返回 500"""
        with patch.dict(sys.modules, {
            'weasyprint': None,
            'weasyprint.text': None,
            'weasyprint.text.fonts': None,
        }):
            resp = admin_client.get(
                f'/reports/delivery/{completed_order.id}'
            )
        assert resp.status_code == 500

    def test_pdf_non_completed_blocked(self, admin_client, sample_order):
        """未完成工单不能下载 PDF"""
        resp = admin_client.get(
            f'/reports/delivery/{sample_order.id}'
        )
        assert resp.status_code == 400
