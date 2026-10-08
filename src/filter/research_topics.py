"""Research scope shared by classification and email labels."""

TOPIC_KEYWORDS = {
    'robot_manipulation': {
        'keywords': ['robot manipulation', 'robotic manipulation', 'robot arm',
                     'robotic arm', 'manipulator', 'dexterous manipulation',
                     'dexterous hand', 'robotic hand', 'in-hand manipulation',
                     'bimanual manipulation', 'robot grasping', 'robotic grasping',
                     'contact-rich manipulation', 'embodied intelligence',
                     'manipulation', 'grasping', 'dexterous hands', 'robot hands',
                     'robotic hands'],
        'weight': 1.0, 'description': '机械臂与灵巧手'},
    'imitation_learning': {
        'keywords': ['imitation learning', 'behavior cloning', 'behaviour cloning',
                     'learning from demonstration', 'learning from demonstrations',
                     'inverse reinforcement learning', 'diffusion policy'],
        'weight': 1.0, 'description': '模仿学习'},
    'vla': {
        'keywords': ['vision-language-action', 'vision language action',
                     'vision-language-action model', 'vla'],
        'weight': 1.0, 'description': 'VLA'},
    'in_context_learning': {
        'keywords': ['in-context learning', 'in context learning',
                     'in-context adaptation', 'in-context reinforcement learning'],
        'weight': 1.0, 'description': 'ICL（上下文学习）'},
    'reinforcement_learning': {
        'keywords': ['reinforcement learning', 'offline rl', 'online rl',
                     'policy optimization', 'policy optimisation',
                     'reinforcement fine-tuning', 'reinforcement finetuning'],
        'weight': 1.0, 'description': '强化学习'},
}

TOPIC_LABELS = {key: value['description'] for key, value in TOPIC_KEYWORDS.items()}

MANIPULATION_KEYWORDS = [
    'manipulation', 'manipulator', 'robot arm', 'robotic arm', 'dexterous',
    'robotic hand', 'robot hand', 'grasping', 'gripper', 'pick-and-place',
    'pick and place', 'bimanual', 'end-effector', 'end effector',
]
ROBOT_CONTEXT = MANIPULATION_KEYWORDS + ['robot', 'robots', 'robotic', 'robotics',
                                        'libero', 'calvin', 'robomimic', 'open x-embodiment']


def matches(text, keyword):
    """Match phrases across whitespace/hyphen variants, with word boundaries."""
    import re
    parts = re.split(r'[\s-]+', keyword.lower())
    return re.search(r'\b' + r'[\s-]+'.join(map(re.escape, parts)) + r'\b', text.lower()) is not None


def scope_rejection(paper, robotics_only=False):
    text = f"{paper.get('title', '')} {paper.get('summary', '')}".lower()
    # Strict exclusion also covers humanoid papers labelled IL/VLA/RL.
    if any(matches(text, term) for term in ['humanoid', 'humanoids', 'humanoid robot', 'human-shaped robot']):
        return '暂不收录人形机器人论文'
    manipulation = any(matches(text, term) for term in MANIPULATION_KEYWORDS)
    method_match = any(matches(text, term) for topic, cfg in TOPIC_KEYWORDS.items()
                       if topic != 'robot_manipulation' for term in cfg['keywords'])
    if robotics_only and not any(matches(text, term) for term in ROBOT_CONTEXT):
        return '仅收录机器人相关论文'
    if not manipulation and any(matches(text, term) for term in [
        'locomotion', 'navigation', 'quadruped', 'quadrupedal', 'drone', 'aerial robot',
    ]):
        return '暂不收录纯移动、步态或飞行任务'
    if not method_match and not manipulation:
        return '具身智能仅收录机械臂、灵巧手与操作任务'
    return None
