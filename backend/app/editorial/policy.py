import copy
import logging
import os

import yaml

logger = logging.getLogger("tech_news.editorial.policy")


class PolicyLoader:
    _cached_policy = None
    _cached_diversity_policy = None

    @classmethod
    def get_policy(cls) -> dict:
        if cls._cached_policy is not None:
            return copy.deepcopy(cls._cached_policy)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(current_dir, "source_profiles.yaml")

        if not os.path.exists(yaml_path):
            logger.warning(f"Policy file {yaml_path} not found. Using default fallback configuration.")
            cls._cached_policy = cls._get_default_policy()
            return copy.deepcopy(cls._cached_policy)

        try:
            with open(yaml_path, encoding="utf-8") as f:
                policy = yaml.safe_load(f)
                if not isinstance(policy, dict):
                    raise ValueError("Policy YAML root must be a dictionary.")
                cls._cached_policy = policy
                logger.info(f"Successfully loaded editorial policy: version={policy.get('policy_version')}")
                return copy.deepcopy(cls._cached_policy)
        except Exception as e:
            logger.error(f"Failed to parse policy YAML: {e}. Falling back to default configuration.")
            cls._cached_policy = cls._get_default_policy()
            return copy.deepcopy(cls._cached_policy)

    @classmethod
    def reset_cache(cls):
        cls._cached_policy = None
        cls._cached_diversity_policy = None

    @classmethod
    def get_diversity_policy(cls) -> dict:
        if cls._cached_diversity_policy is not None:
            return copy.deepcopy(cls._cached_diversity_policy)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(current_dir, "diversity_policy.yaml")

        if not os.path.exists(yaml_path):
            logger.warning(f"Diversity policy file {yaml_path} not found. Using default fallback configuration.")
            cls._cached_diversity_policy = cls._get_default_diversity_policy()
            return copy.deepcopy(cls._cached_diversity_policy)

        try:
            with open(yaml_path, encoding="utf-8") as f:
                policy = yaml.safe_load(f)
                if not isinstance(policy, dict):
                    raise ValueError("Diversity policy YAML root must be a dictionary.")
                cls._cached_diversity_policy = policy
                logger.info(f"Successfully loaded diversity policy.")
                return copy.deepcopy(cls._cached_diversity_policy)
        except Exception as e:
            logger.error(f"Failed to parse diversity policy YAML: {e}. Falling back to default configuration.")
            cls._cached_diversity_policy = cls._get_default_diversity_policy()
            return copy.deepcopy(cls._cached_diversity_policy)

    @staticmethod
    def _get_default_diversity_policy() -> dict:
        return {
            "diversity": {
                "publisher": {
                    "max_per_publisher": 3,
                    "min_publishers_target": 3,
                    "enforcement": "post_ranking"
                },
                "category": {
                    "max_per_category": 4,
                    "enforcement": "post_publisher"
                },
                "topic_dedup": {
                    "similarity_threshold": 0.65,
                    "keep_policy": "highest_score"
                },
                "homepage": {
                    "total_slots": 10,
                    "backfill_policy": "score_order"
                },
                "degradation": {
                    "single_publisher_allowed": True,
                    "single_publisher_log_level": "WARNING"
                }
            }
        }

    @staticmethod
    def _get_default_policy() -> dict:
        return {
            "algorithm_version": "v1",
            "policy_version": "default-fallback",
            "source_authority": {
                "nvidia": 30,
                "google": 30,
                "openai": 30,
                "microsoft": 30,
                "anthropic": 30,
                "apple": 30,
                "github": 30,
                "techcrunch": 20,
                "the verge": 20,
                "ars technica": 20,
                "hacker news": 10,
                "reddit": 10,
            },
            "allow_rss_fallback": [
                "OpenAI Blog",
                "Ars Technica",
            ],
            "html_refresh": {
                "retry_schedule_hours": [1, 6, 24, 168],
                "max_attempts": 4,
            },
            "topic_importance": {
                "artificial_intelligence": 25,
                "security": 25,
                "semiconductors": 25,
                "product_launches": 25,
                "programming": 15,
                "cloud": 15,
                "startups": 15,
                "robotics": 15,
                "general": 5,
            },
            "entity_importance_list": [
                "NVIDIA",
                "Google",
                "OpenAI",
                "Microsoft",
                "AMD",
                "Intel",
                "Apple",
                "Anthropic",
                "Meta",
                "Amazon",
            ],
            "breaking_news_keywords": [
                "breaking",
                "exclusive",
                "major release",
                "security incident",
                "critical breach",
                "zero-day",
            ],
            "reductions": {
                "deal": -20,
                "coupon": -25,
                "sale": -20,
                "discount": -20,
            },
        }


DefinitionName = "PolicyLoader"
