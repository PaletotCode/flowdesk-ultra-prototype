# core/smart_data_analyzer.py
import pandas as pd
import polars as pl
import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from collections import Counter
import logging

@dataclass
class ColumnInfo:
    """Informações sobre uma coluna identificada"""
    name: str
    original_index: int
    data_type: str
    sample_values: List[Any]
    null_percentage: float
    unique_count: int
    is_header_candidate: bool
    confidence_score: float

@dataclass
class DataStructure:
    """Estrutura dos dados identificada"""
    header_row: int
    data_start_row: int
    columns: List[ColumnInfo]
    total_rows: int
    data_rows: int
    patterns: Dict[str, Any]

class SmartDataAnalyzer:
    """
    Analisador inteligente que identifica automaticamente:
    - Linha de cabeçalho
    - Estrutura dos dados
    - Tipos de colunas
    - Padrões de negócio (vendas, pedidos, etc.)
    """
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Padrões para identificar tipos de colunas
        self.column_patterns = {
            'vendedor': ['vendedor', 'vend', 'seller', 'rep', 'representante'],
            'cliente': ['cliente', 'client', 'customer', 'razao', 'empresa'],
            'pedido': ['pedido', 'order', 'num_pedido', 'numero'],
            'data': ['data', 'date', 'dt_', 'datetime'],
            'valor': ['valor', 'preco', 'price', 'total', 'amount', 'vlr'],
            'quantidade': ['qtd', 'quant', 'qty', 'quantidade'],
            'produto': ['produto', 'item', 'product', 'descricao', 'desc'],
            'tipo': ['tipo', 'type', 'categoria', 'class']
        }
    
    def analyze_structure(self, df_raw: pd.DataFrame) -> DataStructure:
        """
        Analisa a estrutura completa do DataFrame bruto
        """
        self.logger.info(f"Iniciando análise estrutural de {df_raw.shape[0]}x{df_raw.shape[1]} células")
        
        # 1. Identifica linha de cabeçalho
        header_row = self._find_header_row(df_raw)
        self.logger.info(f"Linha de cabeçalho identificada: {header_row}")
        
        # 2. Identifica início dos dados
        data_start = self._find_data_start(df_raw, header_row)
        self.logger.info(f"Início dos dados identificado: linha {data_start}")
        
        # 3. Extrai e analisa colunas
        columns = self._analyze_columns(df_raw, header_row, data_start)
        self.logger.info(f"Identificadas {len(columns)} colunas válidas")
        
        # 4. Calcula estatísticas
        total_rows = df_raw.shape[0]
        data_rows = total_rows - data_start if data_start < total_rows else 0
        
        # 5. Identifica padrões de negócio
        patterns = self._identify_business_patterns(df_raw, columns, data_start)
        
        structure = DataStructure(
            header_row=header_row,
            data_start_row=data_start,
            columns=columns,
            total_rows=total_rows,
            data_rows=data_rows,
            patterns=patterns
        )
        
        return structure
    
    def _find_header_row(self, df: pd.DataFrame) -> int:
        """
        Identifica qual linha contém os cabeçalhos das colunas
        """
        best_row = 0
        best_score = 0
        
        # Analisa até as primeiras 20 linhas
        for row_idx in range(min(20, df.shape[0])):
            score = self._score_header_row(df.iloc[row_idx])
            if score > best_score:
                best_score = score
                best_row = row_idx
        
        return best_row
    
    def _score_header_row(self, row: pd.Series) -> float:
        """
        Pontua uma linha baseado na probabilidade de ser cabeçalho
        """
        score = 0
        valid_cells = 0
        
        for cell in row:
            if pd.isna(cell) or str(cell).strip() == '':
                continue
                
            cell_str = str(cell).lower().strip()
            valid_cells += 1
            
            # Pontos por conter palavras-chave de negócio
            for category, patterns in self.column_patterns.items():
                if any(pattern in cell_str for pattern in patterns):
                    score += 10
                    break
            
            # Pontos por ser texto (não número)
            try:
                float(cell_str.replace(',', '.'))
                score -= 2  # Penaliza números em cabeçalhos
            except:
                score += 3  # Favorece texto em cabeçalhos
            
            # Pontos por comprimento apropriado
            if 3 <= len(cell_str) <= 30:
                score += 2
        
        # Normaliza pela quantidade de células válidas
        return score / max(valid_cells, 1)
    
    def _find_data_start(self, df: pd.DataFrame, header_row: int) -> int:
        """
        Identifica onde começam os dados após o cabeçalho
        """
        # Normalmente é logo após o cabeçalho
        start_candidate = header_row + 1
        
        # Verifica se há linhas vazias ou subtítulos
        while start_candidate < min(header_row + 5, df.shape[0]):
            row = df.iloc[start_candidate]
            
            # Conta células com dados
            non_empty = sum(1 for cell in row if not pd.isna(cell) and str(cell).strip() != '')
            
            # Se a linha tem dados suficientes, provavelmente é início dos dados
            if non_empty >= df.shape[1] * 0.3:  # Pelo menos 30% das colunas preenchidas
                return start_candidate
            
            start_candidate += 1
        
        return header_row + 1
    
    def _analyze_columns(self, df: pd.DataFrame, header_row: int, data_start: int) -> List[ColumnInfo]:
        """
        Analisa cada coluna para identificar tipo e características
        """
        columns = []
        header_data = df.iloc[header_row] if header_row < df.shape[0] else pd.Series()
        
        for col_idx in range(df.shape[1]):
            # Nome da coluna
            col_name = str(header_data.iloc[col_idx]) if col_idx < len(header_data) else f"Coluna_{col_idx}"
            col_name = col_name.strip() if col_name != 'nan' else f"Coluna_{col_idx}"
            
            # Dados da coluna (após cabeçalho)
            if data_start < df.shape[0]:
                col_data = df.iloc[data_start:, col_idx]
            else:
                col_data = pd.Series()
            
            # Análise dos dados
            column_info = self._analyze_single_column(col_name, col_idx, col_data)
            
            # Só adiciona colunas com dados relevantes
            if column_info.confidence_score > 0.1:
                columns.append(column_info)
        
        return columns
    
    def _analyze_single_column(self, name: str, index: int, data: pd.Series) -> ColumnInfo:
        """
        Analisa uma única coluna em detalhes
        """
        # Limpa dados nulos
        clean_data = data.dropna()
        clean_data = clean_data[clean_data.astype(str).str.strip() != '']
        
        # Estatísticas básicas
        total_count = len(data)
        valid_count = len(clean_data)
        null_percentage = (total_count - valid_count) / max(total_count, 1) * 100
        unique_count = clean_data.nunique()
        
        # Amostra de valores
        sample_values = clean_data.head(10).tolist()
        
        # Identifica tipo de dados
        data_type = self._identify_data_type(clean_data)
        
        # Verifica se pode ser cabeçalho
        is_header_candidate = self._is_header_candidate(name)
        
        # Calcula score de confiança
        confidence_score = self._calculate_confidence_score(
            valid_count, total_count, unique_count, data_type, name
        )
        
        return ColumnInfo(
            name=name,
            original_index=index,
            data_type=data_type,
            sample_values=sample_values,
            null_percentage=null_percentage,
            unique_count=unique_count,
            is_header_candidate=is_header_candidate,
            confidence_score=confidence_score
        )
    
    def _identify_data_type(self, data: pd.Series) -> str:
        """
        Identifica o tipo de dados predominante na coluna
        """
        if len(data) == 0:
            return 'empty'
        
        # Testa tipos numéricos
        numeric_count = 0
        date_count = 0
        text_count = 0
        
        for value in data.head(min(100, len(data))):
            value_str = str(value).strip()
            
            # Testa numérico
            try:
                float(value_str.replace(',', '.').replace('.', '', value_str.count('.')-1))
                numeric_count += 1
                continue
            except:
                pass
            
            # Testa data
            if self._is_date_like(value_str):
                date_count += 1
                continue
            
            # Resto é texto
            text_count += 1
        
        # Determina tipo predominante
        total = numeric_count + date_count + text_count
        if total == 0:
            return 'unknown'
        
        if numeric_count / total > 0.7:
            return 'numeric'
        elif date_count / total > 0.5:
            return 'date'
        else:
            return 'text'
    
    def _is_date_like(self, value: str) -> bool:
        """
        Verifica se um valor parece ser uma data
        """
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',  # dd/mm/yyyy
            r'\d{4}-\d{1,2}-\d{1,2}',  # yyyy-mm-dd
            r'\d{1,2}-\d{1,2}-\d{4}'   # dd-mm-yyyy
        ]
        
        return any(re.match(pattern, value) for pattern in date_patterns)
    
    def _is_header_candidate(self, name: str) -> bool:
        """
        Verifica se o nome pode ser um cabeçalho válido
        """
        name_lower = name.lower().strip()
        
        # Verifica se contém palavras-chave de negócio
        for patterns in self.column_patterns.values():
            if any(pattern in name_lower for pattern in patterns):
                return True
        
        return False
    
    def _calculate_confidence_score(self, valid_count: int, total_count: int, 
                                  unique_count: int, data_type: str, name: str) -> float:
        """
        Calcula um score de confiança para a coluna
        """
        if total_count == 0:
            return 0.0
        
        score = 0.0
        
        # Score baseado na quantidade de dados válidos
        fill_rate = valid_count / total_count
        score += fill_rate * 0.4
        
        # Score baseado no tipo de dados
        type_scores = {'numeric': 0.3, 'date': 0.3, 'text': 0.2, 'empty': 0.0, 'unknown': 0.1}
        score += type_scores.get(data_type, 0.1)
        
        # Score baseado na relevância do nome
        if self._is_header_candidate(name):
            score += 0.3
        
        # Penaliza colunas com poucos dados únicos (exceto para IDs)
        if unique_count < 3 and data_type != 'text':
            score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _identify_business_patterns(self, df: pd.DataFrame, columns: List[ColumnInfo], 
                                  data_start: int) -> Dict[str, Any]:
        """
        Identifica padrões específicos do negócio (vendas, pedidos, etc.)
        """
        patterns = {
            'vendedor_columns': [],
            'cliente_columns': [],
            'valor_columns': [],
            'pedido_columns': [],
            'data_columns': [],
            'produto_columns': []
        }
        
        # Mapeia colunas para categorias de negócio
        for col in columns:
            col_name_lower = col.name.lower()
            
            for category, keywords in self.column_patterns.items():
                if any(keyword in col_name_lower for keyword in keywords):
                    patterns[f'{category}_columns'].append(col)
                    break
        
        # Identifica colunas de valor/monetárias
        for col in columns:
            if col.data_type == 'numeric':
                # Verifica se os valores parecem monetários
                if data_start < df.shape[0]:
                    sample_data = df.iloc[data_start:data_start+100, col.original_index].dropna()
                    if len(sample_data) > 0:
                        avg_value = sample_data.astype(str).apply(
                            lambda x: self._try_parse_numeric(x)
                        ).mean()
                        
                        # Se a média é alta, provavelmente é valor monetário
                        if avg_value > 10:
                            patterns['valor_columns'].append(col)
        
        return patterns
    
    def _try_parse_numeric(self, value: str) -> float:
        """
        Tenta converter um valor para numérico
        """
        try:
            clean_value = str(value).replace(',', '.').strip()
            return float(clean_value)
        except:
            return 0.0
    
    def create_clean_dataframe(self, df_raw: pd.DataFrame, structure: DataStructure) -> pl.DataFrame:
        """
        Cria um DataFrame limpo e estruturado baseado na análise
        """
        self.logger.info("Criando DataFrame limpo...")
        
        # Extrai dados a partir da linha identificada
        if structure.data_start_row >= df_raw.shape[0]:
            raise ValueError("Nenhum dado encontrado após análise estrutural")
        
        # Seleciona apenas colunas confiáveis
        good_columns = [col for col in structure.columns if col.confidence_score > 0.3]
        
        if not good_columns:
            raise ValueError("Nenhuma coluna confiável identificada")
        
        # Cria DataFrame com dados limpos
        clean_data = {}
        for col in good_columns:
            col_data = df_raw.iloc[structure.data_start_row:, col.original_index]
            
            # Limpa a coluna
            clean_col = self._clean_column_data(col_data, col.data_type)
            clean_data[col.name] = clean_col
        
        # Adiciona ID de linha original
        clean_data['id_linha_original'] = range(1, len(clean_col) + 1)
        
        # Converte para Polars
        df_polars = pl.DataFrame(clean_data)
        
        self.logger.info(f"DataFrame limpo criado: {df_polars.shape[0]}x{df_polars.shape[1]}")
        return df_polars
    
    def _clean_column_data(self, data: pd.Series, data_type: str) -> List[Any]:
        """
        Limpa os dados de uma coluna baseado no seu tipo
        """
        cleaned = []
        
        for value in data:
            if pd.isna(value) or str(value).strip() == '':
                cleaned.append(None)
                continue
            
            if data_type == 'numeric':
                cleaned.append(self._try_parse_numeric(str(value)))
            elif data_type == 'date':
                # Mantém como string por enquanto
                cleaned.append(str(value).strip())
            else:
                cleaned.append(str(value).strip())
        
        return cleaned