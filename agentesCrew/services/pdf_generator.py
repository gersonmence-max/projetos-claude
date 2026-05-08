"""
PDF Generator Service
=====================
Gera Site Sheet, Letter of Intent (LOI) e Carta de Apresentação
para oportunidades de carregadores EV em Massachusetts.

Integra-se ao fluxo de scoring existente:
- Recebe dados já calculados do /api/busca-ma
- Gera PDFs profissionais
- Retorna ZIP com todos os PDFs
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    PageBreak, Image, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from datetime import datetime, timedelta
import io
import zipfile
from pathlib import Path

class PDFGenerator:
    """Gera documentos profissionais para oportunidades EV"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._criar_estilos_customizados()
    
    def _criar_estilos_customizados(self):
        """Define estilos customizados para os documentos"""
        self.styles.add(ParagraphStyle(
            name='TituloRelatorio',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a73e8'),
            spaceAfter=30,
            alignment=1,  # center
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SubTitulo',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#333333'),
            spaceAfter=20,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CorpoTexto',
            parent=self.styles['BodyText'],
            fontSize=10,
            leading=14,
            alignment=4,  # justified
            textColor=colors.HexColor('#333333')
        ))
        
        self.styles.add(ParagraphStyle(
            name='Legenda',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
            alignment=4
        ))
    
    def gerar_site_sheet(self, locacao_data):
        """
        Gera Site Sheet profissional
        
        Args:
            locacao_data: dict com dados da location
                {
                    'name': str,
                    'address': str,
                    'lat': float,
                    'lng': float,
                    'rating': float,
                    'reviews': int,
                    'type': str,
                    'dcfc': dict (resultado do scoring),
                    'level2': dict (resultado do scoring),
                    ...
                }
        
        Returns:
            bytes: PDF em formato bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        story = []
        
        # HEADER
        story.append(self._criar_header_site_sheet(locacao_data))
        story.append(Spacer(1, 0.3*inch))
        
        # INFORMACOES BASICAS
        story.append(Paragraph("Location Information", self.styles['SubTitulo']))
        story.append(self._criar_tabela_info_basica(locacao_data))
        story.append(Spacer(1, 0.2*inch))
        
        # SCORES COMPARATIVOS
        story.append(Paragraph("Viability Analysis - DCFC vs Level 2", self.styles['SubTitulo']))
        story.append(self._criar_tabela_scores(locacao_data))
        story.append(Spacer(1, 0.2*inch))
        
        # BREAKDOWN DETALHADO
        story.append(PageBreak())
        story.append(Paragraph("Detailed Scoring Breakdown", self.styles['SubTitulo']))
        story.append(self._criar_breakdown_detalhado(locacao_data))
        story.append(Spacer(1, 0.2*inch))
        
        # RECOMENDACOES
        story.append(Paragraph("Recommendations", self.styles['SubTitulo']))
        story.append(self._criar_recomendacoes(locacao_data))
        
        # FOOTER
        story.append(Spacer(1, 0.3*inch))
        story.append(self._criar_footer_site_sheet(locacao_data))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def gerar_loi(self, locacao_data, empresa_info):
        """
        Gera Letter of Intent (LOI) profissional
        
        Args:
            locacao_data: dict com dados da location
            empresa_info: dict com dados da empresa
                {
                    'nome': str,
                    'endereco': str,
                    'email': str,
                    'telefone': str,
                    'representante': str
                }
        
        Returns:
            bytes: PDF em formato bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )
        
        story = []
        
        # DATA E ENDERECO
        data_hoje = datetime.now()
        story.append(Paragraph(
            f"{data_hoje.strftime('%d de %B de %Y')}",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 0.3*inch))
        
        # DESTINATARIO (placeholder - será preenchido manualmente)
        story.append(Paragraph("[Recipient Name]<br/>[Recipient Title]<br/>[Location Name]<br/>[Address]", 
                             self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # ABERTURA
        story.append(Paragraph("Dear [Recipient Name],", self.styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # CORPO DO LOI
        corpo_loi = f"""
        This Letter of Intent ("LOI") outlines our interest in developing a sustainable electric vehicle (EV) charging station 
        at <b>{locacao_data['name']}</b>, located at {locacao_data['address']}.
        <br/><br/>
        <b>LOCATION DETAILS:</b><br/>
        Location: {locacao_data['name']}<br/>
        Address: {locacao_data['address']}<br/>
        Type: {locacao_data['type']}<br/>
        Rating: {locacao_data['rating']}/5.0 ({locacao_data['reviews']} reviews)<br/>
        <br/>
        
        <b>VIABILITY ASSESSMENT:</b><br/>
        Based on comprehensive analysis using our EV Viability Platform:
        <br/>
        """
        
        if locacao_data.get('dcfc'):
            dcfc = locacao_data['dcfc']
            corpo_loi += f"""
            DC Fast Charging (DCFC) Viability: {dcfc['final_score']:.1f}/10 ({dcfc['potential']})<br/>
            """
        
        if locacao_data.get('level2'):
            l2 = locacao_data['level2']
            corpo_loi += f"""
            Level 2 AC Charging Viability: {l2['final_score']:.1f}/10 ({l2['potential']})<br/>
            """
        
        corpo_loi += """
        <br/>
        <b>PROPOSED NEXT STEPS:</b><br/>
        1. Site visit and feasibility assessment<br/>
        2. Electrical infrastructure evaluation<br/>
        3. Permitting and regulatory compliance review<br/>
        4. Formal partnership negotiation<br/>
        5. Installation and commissioning<br/>
        <br/>
        
        <b>TIMELINE:</b><br/>
        We propose completing the initial assessment within 30 days and moving to formal negotiations within 60 days.
        <br/><br/>
        
        This LOI represents our genuine interest in collaborating on this EV charging opportunity. 
        We look forward to discussing how we can work together to advance sustainable transportation in Massachusetts.
        <br/><br/>
        """
        
        story.append(Paragraph(corpo_loi, self.styles['CorpoTexto']))
        story.append(Spacer(1, 0.3*inch))
        
        # ASSINATURA
        story.append(Paragraph("Sincerely,<br/><br/><br/>", self.styles['Normal']))
        story.append(Paragraph("[Your Name]<br/>[Your Title]<br/>", self.styles['Normal']))
        
        if empresa_info:
            story.append(Paragraph(
                f"{empresa_info.get('nome', '')}<br/>{empresa_info.get('email', '')}<br/>{empresa_info.get('telefone', '')}",
                self.styles['Normal']
            ))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def gerar_carta_apresentacao(self, locacao_data, empresa_info):
        """
        Gera Carta de Apresentação profissional
        
        Args:
            locacao_data: dict com dados da location
            empresa_info: dict com dados da empresa
        
        Returns:
            bytes: PDF em formato bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )
        
        story = []
        
        # HEADER COM LOGO (placeholder)
        header_style = ParagraphStyle(
            'Header',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor('#1a73e8'),
            fontName='Helvetica-Bold',
            alignment=0
        )
        
        story.append(Paragraph("EV VIABILITY PLATFORM", header_style))
        story.append(Paragraph("Massachusetts Charging Opportunity Analysis", self.styles['Legenda']))
        story.append(Spacer(1, 0.5*inch))
        
        # DATA
        data_hoje = datetime.now()
        story.append(Paragraph(
            f"{data_hoje.strftime('%d de %B de %Y')}",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 0.3*inch))
        
        # CORPO DA CARTA
        corpo = f"""
        <b>RE: EV Charging Station Opportunity - {locacao_data['name']}</b>
        <br/><br/>
        Dear Property Manager / Owner,
        <br/><br/>
        
        We are pleased to present an exciting opportunity to enhance your property with a modern electric vehicle (EV) 
        charging station at <b>{locacao_data['name']}</b>.
        <br/><br/>
        
        <b>WHY THIS LOCATION?</b><br/>
        Our advanced EV Viability Analysis Platform has identified your location as a prime candidate due to:
        <br/>
        • Strategic location with high foot traffic potential<br/>
        • Strong EV adoption in surrounding area<br/>
        • Optimal infrastructure compatibility<br/>
        • Revenue generation opportunity for your property<br/>
        <br/>
        
        <b>THE OPPORTUNITY:</b><br/>
        """
        
        # Adicionar scores se disponíveis
        if locacao_data.get('dcfc') or locacao_data.get('level2'):
            corpo += "Our analysis shows strong viability for:<br/>"
            if locacao_data.get('dcfc'):
                dcfc = locacao_data['dcfc']
                corpo += f"• DC Fast Charging: Viability Score {dcfc['final_score']:.1f}/10<br/>"
            if locacao_data.get('level2'):
                l2 = locacao_data['level2']
                corpo += f"• Level 2 AC Charging: Viability Score {l2['final_score']:.1f}/10<br/>"
            corpo += "<br/>"
        
        corpo += """
        <b>WHAT WE OFFER:</b><br/>
        • Professional site assessment<br/>
        • Infrastructure planning and design<br/>
        • Permitting and regulatory guidance<br/>
        • Installation and ongoing maintenance<br/>
        • Revenue sharing model<br/>
        <br/>
        
        <b>NEXT STEPS:</b><br/>
        We would like to schedule a brief meeting to discuss this opportunity in detail. 
        We are confident that this partnership will be mutually beneficial and align with current sustainability trends.
        <br/><br/>
        
        Please contact us at your earliest convenience to arrange a site visit and consultation.
        <br/><br/>
        """
        
        story.append(Paragraph(corpo, self.styles['CorpoTexto']))
        story.append(Spacer(1, 0.3*inch))
        
        # ASSINATURA
        story.append(Paragraph("Best regards,<br/><br/><br/>", self.styles['Normal']))
        
        if empresa_info:
            story.append(Paragraph(
                f"{empresa_info.get('representante', '[Your Name]')}<br/>{empresa_info.get('nome', '')}<br/>"
                f"Email: {empresa_info.get('email', '[email]')}<br/>Phone: {empresa_info.get('telefone', '[phone]')}",
                self.styles['Normal']
            ))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def gerar_zip_completo(self, locacoes_list, empresa_info=None):
        """
        Gera ZIP com Site Sheet, LOI e Carta para múltiplas locações
        
        Args:
            locacoes_list: lista de dicts com dados das locations
            empresa_info: dict com dados da empresa (opcional)
        
        Returns:
            bytes: ZIP em formato bytes
        """
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for idx, locacao in enumerate(locacoes_list, 1):
                nome_local = locacao['name'].replace(' ', '_').replace('/', '_')[:30]
                
                # Site Sheet
                site_sheet = self.gerar_site_sheet(locacao)
                zip_file.writestr(
                    f"{idx:02d}_{nome_local}_SiteSheet.pdf",
                    site_sheet
                )
                
                # LOI
                loi = self.gerar_loi(locacao, empresa_info)
                zip_file.writestr(
                    f"{idx:02d}_{nome_local}_LOI.pdf",
                    loi
                )
                
                # Carta
                carta = self.gerar_carta_apresentacao(locacao, empresa_info)
                zip_file.writestr(
                    f"{idx:02d}_{nome_local}_Carta.pdf",
                    carta
                )
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    
    # METODOS AUXILIARES
    
    def _criar_header_site_sheet(self, locacao_data):
        """Cria header do Site Sheet"""
        return Paragraph(
            f"<b>SITE SHEET</b><br/>{locacao_data['name']}<br/>"
            f"<font size=8>{locacao_data['address']}</font>",
            self.styles['TituloRelatorio']
        )
    
    def _criar_tabela_info_basica(self, locacao_data):
        """Cria tabela com informações básicas"""
        data = [
            ['Property Name', locacao_data['name']],
            ['Address', locacao_data['address']],
            ['Type', locacao_data['type']],
            ['Rating', f"{locacao_data['rating']}/5.0 ({locacao_data['reviews']} reviews)"],
            ['Latitude', f"{locacao_data['lat']:.6f}"],
            ['Longitude', f"{locacao_data['lng']:.6f}"],
        ]
        
        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        return table
    
    def _criar_tabela_scores(self, locacao_data):
        """Cria tabela comparativa de scores"""
        data = [['Metric', 'DCFC', 'Level 2']]
        
        if locacao_data.get('dcfc'):
            dcfc = locacao_data['dcfc']
            data.append(['Score', f"{dcfc['final_score']:.1f}/10", 
                        f"{locacao_data.get('level2', {}).get('final_score', 'N/A')}/10"])
            data.append(['Viability', dcfc['potential'], 
                        f"{locacao_data.get('level2', {}).get('potential', 'N/A')}"])
            data.append(['Confidence', f"{int(dcfc['confidence']*100)}%", 
                        f"{int(locacao_data.get('level2', {}).get('confidence', 0)*100)}%"])
            data.append(['Demand', f"{dcfc['breakdown']['demand']:.1f}", 
                        f"{locacao_data.get('level2', {}).get('breakdown', {}).get('demand', 'N/A')}"])
            data.append(['Competition', f"{dcfc['breakdown']['competition']:.1f}", 
                        f"{locacao_data.get('level2', {}).get('breakdown', {}).get('competition', 'N/A')}"])
        
        table = Table(data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        return table
    
    def _criar_breakdown_detalhado(self, locacao_data):
        """Cria breakdown detalhado dos 4 motores"""
        story = []
        
        if locacao_data.get('dcfc'):
            story.append(Paragraph("<b>DC Fast Charging (DCFC)</b>", self.styles['Normal']))
            dcfc = locacao_data['dcfc']
            
            bd_data = [
                ['Motor', 'Score', 'Weight'],
                ['Demand (Traffic)', f"{dcfc['breakdown']['demand']:.1f}/10", '35%'],
                ['Competition', f"{dcfc['breakdown']['competition']:.1f}/10", '30%'],
                ['Site Fit', f"{dcfc['breakdown']['site_fit']:.1f}/10", '20%'],
                ['EV Affinity', f"{dcfc['breakdown']['ev_affinity']:.1f}/10", '15%'],
            ]
            
            table = Table(bd_data, colWidths=[2*inch, 1.5*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4285f4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 0.2*inch))
        
        if locacao_data.get('level2'):
            story.append(Paragraph("<b>Level 2 AC Charging</b>", self.styles['Normal']))
            l2 = locacao_data['level2']
            
            bd_data = [
                ['Motor', 'Score', 'Weight'],
                ['Demand (Traffic)', f"{l2['breakdown']['demand']:.1f}/10", '25%'],
                ['Competition', f"{l2['breakdown']['competition']:.1f}/10", '20%'],
                ['Site Fit', f"{l2['breakdown']['site_fit']:.1f}/10", '35%'],
                ['EV Affinity', f"{l2['breakdown']['ev_affinity']:.1f}/10", '20%'],
            ]
            
            table = Table(bd_data, colWidths=[2*inch, 1.5*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34a853')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            
            story.append(table)
        
        return story
    
    def _criar_recomendacoes(self, locacao_data):
        """Cria recomendações baseadas nos scores"""
        story = []
        
        best_option = None
        best_score = 0
        
        if locacao_data.get('dcfc') and locacao_data['dcfc']['final_score'] > best_score:
            best_option = 'DCFC'
            best_score = locacao_data['dcfc']['final_score']
        
        if locacao_data.get('level2') and locacao_data['level2']['final_score'] > best_score:
            best_option = 'Level 2'
            best_score = locacao_data['level2']['final_score']
        
        recomendacao = f"""
        <b>Best Option:</b> {best_option} with a viability score of {best_score:.1f}/10<br/><br/>
        
        <b>Key Findings:</b><br/>
        • Location type: {locacao_data['type']}<br/>
        • Customer base: {locacao_data['rating']}/5.0 rating<br/>
        • Infrastructure readiness: To be assessed on site<br/>
        <br/>
        
        <b>Recommended Actions:</b><br/>
        1. Schedule site assessment<br/>
        2. Evaluate electrical infrastructure<br/>
        3. Check local permitting requirements<br/>
        4. Confirm property owner interest<br/>
        5. Prepare financial projections<br/>
        """
        
        story.append(Paragraph(recomendacao, self.styles['CorpoTexto']))
        return story
    
    def _criar_footer_site_sheet(self, locacao_data):
        """Cria footer do documento"""
        return Paragraph(
            f"<font size=7>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>"
            f"Location: {locacao_data['name']}</font>",
            self.styles['Legenda']
        )
