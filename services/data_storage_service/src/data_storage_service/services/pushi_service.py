"""Сервис для работы с Pushi."""

from pathlib import Path
from typing import List, Dict, Any, Optional
from service.utils.logger import get_logger
from service.services.base_service import BaseService

from pushi.config.factory import ConfigFactory
from pushi.connectors.factory import ConnectorFactory
from pushi.pipeline.pipeline import Pipeline
from pushi.playground.playground import Playground
from pushi.rules import RuleRegistry
from pushi.utils.path_utils import path_to_config as default_path_to_config
from pushi.scripts.get_path_to_csv import get_path_to_csv
from pushi.scripts.get_texts_from_csv import get_texts_from_csv
from pushi.services import create_services
from pushi.rules.base_rule import BaseRule, RuleConfig, config_transfer

from pydantic import BaseModel

logger = get_logger(__name__)


def _to_pushi_dict(rule: dict) -> dict:
    """Map snapshot rule dict to the format expected by pushi's config_transfer.

    Snapshot keys          →  pushi config_transfer keys
    ─────────────────────────────────────────────────────
    product_types (plural) →  product_type  (singular)
    channel_types (plural) →  channel_type  (singular)
    additional_instructions (str) → prompts {"additional_instructions": ...}
    patterns (dict)        →  patterns (unchanged)
    """
    out = dict(rule)

    # Plural → singular
    if "product_type" not in out:
        out["product_type"] = out.get("product_types", [])
    if "channel_type" not in out:
        out["channel_type"] = out.get("channel_types", [])

    # Build prompts dict
    if "prompts" not in out or not out["prompts"]:
        ai = out.get("additional_instructions")
        out["prompts"] = {"additional_instructions": ai} if ai else {}

    # Ensure patterns is a dict
    if "patterns" not in out or out["patterns"] is None:
        out["patterns"] = {}

    return out




class PlaygroundService(BaseService):

    def __init__(self):
        self.config = None

    def _setup_playground(
        self,
        path_to_config: str = None,
        rules: Optional[List[Dict[str, Any]]] = None
    ):
        if path_to_config:
            self.config = ConfigFactory.load_config(Path(path_to_config))
        elif self.config is None:
            try:
                self.config = ConfigFactory.load_config(default_path_to_config())
            except Exception as e:
                raise RuntimeError(
                    f"No config provided and default config not found: {e}"
                ) from e
        if rules:
            self.config.rules = [config_transfer(_to_pushi_dict(r)) for r in rules]
        simple_rules = RuleRegistry.create_simple_rules(self.config, None)
        try:
            llm_connector = ConnectorFactory.create_connector(self.config.llm)
        except Exception as e:
            logger.warning(f"Не удалось создать LLM коннектор: {e}")
            llm_connector = None
        llm_rules = []
        combined_rules = []
        if llm_connector:
            llm_rules = RuleRegistry.create_llm_rules(self.config, llm_connector, None)
            combined_rules = RuleRegistry.create_combined_rules(self.config, llm_connector, None)
        all_rules = simple_rules + llm_rules + combined_rules
        playground = Playground(all_rules)
        rule_ids = [rule.__dict__.get("config").rule_id for rule in all_rules]
        return playground, rule_ids

    def get_rule_info(self, risk_id: str):
        for rule in self.all_rules:
            rule_config = rule.__dict__.get("config")
            if rule_config and rule_config.rule_id.startswith(risk_id):
                return rule_config.rule_info

    async def process_batch(self,
        communications: List[Dict[str, Any]],
        rules_list: List[Dict[str, Any]],
        config_path: str = None
    ) -> List[Dict[str, Any]]:
        playground, rule_ids = self._setup_playground(path_to_config=config_path, rules=rules_list)
        try:
            results = await playground.evaluate_multiple_pushes_multiple_rules(
                communications,
                rule_ids=rule_ids
            )
            return results
        except Exception as e:
            logger.error(f"Ошибка обработки пакета через Playground: {str(e)}", exc_info=True)
            raise



class PipelineService(BaseService):
    
    def __init__(self):
        self.config = None

    def _setup_pipeline(
        self,
        dataset_path: str,
        rules: Optional[List[Dict[str, Any]]] = None,
        path_to_config: str = None,
        format_file: Optional[str] = 'xlsx',
    ):

        if path_to_config:
            self.config = ConfigFactory.load_config(Path(path_to_config))
        elif self.config is None:
            try:
                self.config = ConfigFactory.load_config(default_path_to_config())
            except Exception as e:
                raise RuntimeError(
                    f"No config provided and default config not found: {e}"
                ) from e
        if rules:
            self.config.rules = [config_transfer(_to_pushi_dict(r)) for r in rules]
        
        path_to_csv: Optional[Path] = None
        required_annotators = self.config.data_processing.required_annotators
        path_to_csv = get_path_to_csv(dataset_path, format_file, required_annotators)
        if not path_to_csv:
            raise FileNotFoundError(f"Не найден CSV файл с необходимыми аннотаторами в директории {dataset_path}")

        texts = get_texts_from_csv(path_to_csv)

        services = create_services(self.config, None)

        context = {
            "texts": texts,
            "config": self.config,
            "services_count": len(services),
            "include_risk_ids": None,
        }

        pipeline = Pipeline(services)

        return pipeline, context, services

    async def process_pipe(
        self,
        dataset_path: str,
        rules_list: List[Dict[str, Any]] = None,
        config_path: str = None,
        format_file: Optional[str] = 'xlsx',
    ) -> dict:

        pipeline, context, services = self._setup_pipeline(
            dataset_path=dataset_path,
            rules=rules_list,
            path_to_config=config_path,
            format_file=format_file
        )

        try:
            context = await pipeline.run(context)
            return context
        except Exception as e:
            logger.error(f"Ошибка обработки через Pipeline: {str(e)}", exc_info=True)
            raise
        finally:
            for service in services:
                if hasattr(service, "aclose"):
                    try:
                        await service.aclose()
                    except Exception as e:
                        logger.warning(
                            f"Ошибка при закрытии сервиса {getattr(service.config, 'name', str(service))}: {e}"
                        )

