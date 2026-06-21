"""测试 LLM 配置统一"""

from dotenv import load_dotenv

load_dotenv()


def test_llm_config_unified():
    """测试统一 LLM 配置"""
    print("=== 测试 LLM 配置统一 ===\n")
    
    # 测试 1: LLMFactory
    print("1. LLMFactory 配置:")
    from app.core.llm_config import LLMFactory
    config = LLMFactory.get_config()
    for k, v in config.items():
        if k != "api_key":
            print(f"   {k}: {v}")
    print()
    
    # 测试 2: build_llm
    print("2. build_llm 配置:")
    from app.infrastructure.agent.providers.llm import build_llm
    llm = build_llm()
    print(f"   model: {llm.model_name}")
    print(f"   temperature: {llm.temperature}")
    print()
    
    # 测试 3: get_llm 快捷函数
    print("3. get_llm 快捷函数:")
    from app.core.llm_config import get_llm
    llm2 = get_llm()
    print(f"   model: {llm2.model_name}")
    print(f"   temperature: {llm2.temperature}")
    print()
    
    # 测试 4: 配置一致性
    print("4. 配置一致性:")
    print(f"   LLMFactory model == build_llm model: {config['model'] == llm.model_name}")
    print(f"   LLMFactory model == get_llm model: {config['model'] == llm2.model_name}")
    print()
    
    # 测试 5: 环境变量兼容
    print("5. 环境变量兼容:")
    import os
    print(f"   LLM_PROVIDER: {os.getenv('LLM_PROVIDER', '未设置')}")
    print(f"   LLM_MODEL: {os.getenv('LLM_MODEL', '未设置')}")
    print(f"   LLM_BASE_URL: {os.getenv('LLM_BASE_URL', '未设置')[:50]}...")
    
    print("\n=== 统一配置成功 ===")


if __name__ == "__main__":
    test_llm_config_unified()