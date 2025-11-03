import json
from utils.paper_retriever import RetrieverFactory
from utils.llms_api import APIHelper
from utils.header import ConfigReader
from utils.hash import check_env, check_embedding
from generator import IdeaGenerator
import functools


class Backend(object):
    def __init__(self) -> None:
        CONFIG_PATH = "./configs/datasets.yaml"
        EXAMPLE_PATH = "./assets/data/example.json"
        USE_INSPIRATION = True
        BRAINSTORM_MODE = "mode_c"

        self.config = ConfigReader.load(CONFIG_PATH)
        check_env()
        check_embedding(self.config.DEFAULT.embedding)
        RETRIEVER_NAME = self.config.RETRIEVE.retriever_name
        self.api_helper = APIHelper(self.config)
        self.retriever_factory = (
            RetrieverFactory.get_retriever_factory().create_retriever(
                RETRIEVER_NAME, self.config
            )
        )
        self.idea_generator = IdeaGenerator(self.config, None)
        self.use_inspiration = USE_INSPIRATION
        self.brainstorm_mode = BRAINSTORM_MODE
        self.examples = self.load_examples(EXAMPLE_PATH)

    def load_examples(self, path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading examples from {path}: {e}")
            return []
        
    def background2entities_callback(self, background):
        return self.api_helper.generate_entity_list(background)

    def background2expandedbackground_callback(self, background, entities):
        # 处理 entities 为 None 或空列表的情况
        if entities is None:
            entities = []
        if not isinstance(entities, (list, tuple)):
            entities = list(entities) if entities else []
        
        # 如果 entities 为空，使用空字符串
        if len(entities) == 0:
            keywords_str = ""
        else:
            keywords_str = functools.reduce(lambda x, y: f"{x}, {y}", entities)
        
        try:
            expanded_background = self.api_helper.expand_background(background, keywords_str)
        except Exception as e:
            # 记录详细错误信息
            print(f"Error in background2expandedbackground_callback: {type(e).__name__}: {e}")
            return None
        
        return expanded_background

    def background2brainstorm_callback(self, expanded_background):
        return self.api_helper.generate_brainstorm(expanded_background)

    def brainstorm2entities_callback(self, brainstorm, entities):
        # 检查输入参数是否为 None
        if brainstorm is None:
            print("Warning: brainstorm is None, skipping entity extraction from brainstorm")
            entities_bs = []
        else:
            entities_bs = self.api_helper.generate_entity_list(brainstorm, 10)
            # 检查返回结果
            if entities_bs is None:
                entities_bs = []
        
        # 检查 entities 是否为 None
        if entities is None:
            entities = []
        
        # 确保都是列表
        if not isinstance(entities, (list, tuple)):
            entities = list(entities) if entities else []
        if not isinstance(entities_bs, (list, tuple)):
            entities_bs = list(entities_bs) if entities_bs else []
        
        entities_all = list(set(entities) | set(entities_bs))
        return entities_all

    def upload_json_callback(self, input):
        with open(input, "r") as json_file:
            contents = json_file.read()
            json_contents = json.loads(contents)
        return [json_contents["background"], contents]

    def entities2literature_callback(self, expanded_background, entities):
        result = self.retriever_factory.retrieve(
            expanded_background, entities, need_evaluate=False, target_paper_id_list=[]
        )
        res = []
        for i, p in enumerate(result["related_paper"]):
            res.append(f'{p["title"]}. {p["venue_name"].upper()} {p["year"]}.')
        return res, result["related_paper"]

    def literature2initial_ideas_callback(
        self, expanded_background, brainstorms, retrieved_literature
    ):
        self.idea_generator.paper_list = retrieved_literature
        self.idea_generator.brainstorm = brainstorms
        _, _, inspirations, initial_ideas, idea_filtered, final_ideas = (
            self.idea_generator.generate_ins_bs(expanded_background)
        )
        return idea_filtered, final_ideas

    def initial2final_callback(self, initial_ideas, final_ideas):
        return final_ideas

    def get_demo_i(self, i):
        if 0 <= i < len(self.examples):
            return self.examples[i].get("background", "Background not found.")
        else:
            return "Example not found. Please select a valid index."
