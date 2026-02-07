from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch
import pandas as pd

from scompras_app.models import (
    Departamento,
    Insumo,
    InsumoSolicitud,
    Seccion,
    SolicitudCompra,
)


class ImportarInsumosTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin',
            password='password',
            is_superuser=True,
        )
        self.departamento = Departamento.objects.create(
            id_departamento='DEP-01',
            nombre='Departamento 1',
            abreviatura='DEP',
        )
        self.seccion = Seccion.objects.create(
            nombre='Seccion 1',
            abreviatura='SEC',
            departamento=self.departamento,
        )
        self.solicitud = SolicitudCompra.objects.create(
            seccion=self.seccion,
            usuario=self.user,
            descripcion='Solicitud de prueba',
        )
        self.insumo = Insumo.objects.create(
            renglon=1,
            codigo_insumo='INS-001',
            nombre='Insumo anterior',
            caracteristicas='Original',
            nombre_presentacion='Caja',
            cantidad_unidad_presentacion='1',
            codigo_presentacion='PRES-001',
            fecha_actualizacion=timezone.now(),
        )
        InsumoSolicitud.objects.create(
            solicitud=self.solicitud,
            insumo=self.insumo,
            cantidad=2,
        )

    @patch('scompras_app.views.pd.read_excel')
    def test_importacion_catalogo_no_rompe_fk(self, mock_read_excel):
        mock_read_excel.return_value = pd.DataFrame(
            [
                {
                    'RENGLÓN': 1,
                    'CÓDIGO DE INSUMO': 'INS-001',
                    'NOMBRE': 'Insumo actualizado',
                    'CARACTERÍSTICAS': 'Actualizado',
                    'NOMBRE DE LA PRESENTACIÓN': 'Caja',
                    'CANTIDAD Y UNIDAD DE MEDIDA DE LA PRESENTACIÓN': '1',
                    'CÓDIGO DE PRESENTACIÓN': 'PRES-001',
                },
                {
                    'RENGLÓN': 2,
                    'CÓDIGO DE INSUMO': 'INS-002',
                    'NOMBRE': 'Insumo nuevo',
                    'CARACTERÍSTICAS': 'Nuevo',
                    'NOMBRE DE LA PRESENTACIÓN': 'Bolsa',
                    'CANTIDAD Y UNIDAD DE MEDIDA DE LA PRESENTACIÓN': '5',
                    'CÓDIGO DE PRESENTACIÓN': 'PRES-002',
                },
            ]
        )

        self.client.force_login(self.user)
        archivo = SimpleUploadedFile('insumos.xlsx', b'contenido')
        response = self.client.post(
            reverse('scompras:importar_excel'),
            data={
                'archivo_excel': archivo,
                'fechainsumo': timezone.now().date(),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.insumo.refresh_from_db()
        self.assertEqual(self.insumo.nombre, 'Insumo actualizado')
        self.assertTrue(
            InsumoSolicitud.objects.filter(
                solicitud=self.solicitud,
                insumo=self.insumo,
            ).exists()
        )
        self.assertEqual(Insumo.objects.count(), 2)
