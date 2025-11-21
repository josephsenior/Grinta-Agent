from tree_sitter import Parser
from tree_sitter_language_pack import get_language

# Use installed language pack instead of local third_party grammar
LANGUAGE = get_language("python")


def get_all_sub_trees(root_node):
    sub_tree_sexp_list = []
    depth = 1
    node_stack = [[root_node, depth]]
    while node_stack:
        cur_node, cur_depth = node_stack.pop()
        if cur_node.child_count > 0:
            sub_tree_sexp_list.append(
                [cur_node.sexp(), cur_depth, cur_node, cur_node.children[0].text]
            )
        else:
            sub_tree_sexp_list.append([cur_node.sexp(), cur_depth, cur_node, None])
        for child_node in cur_node.children:
            if len(child_node.children) != 0:
                depth = cur_depth + 1
                node_stack.append([child_node, depth])
    return sub_tree_sexp_list


def ast_parse(candidate):
    parser = Parser(LANGUAGE)
    return parser.parse(bytes(candidate, "utf8")).root_node


def get_args(node):
    if node.child_count == 0:
        return []
    args_list = []
    for child in node.children[0].children[0].children[1].children:
        if "model=" in child.text.decode() or "model =" in child.text.decode():
            args_list.append(child.children[2].text)
        elif child.text.decode() not in ["(", ")", ","]:
            args_list.append(child.text)
    return args_list


def ast_check(candidate_subtree_list, base_tree_list):
    for idx, base_tree in enumerate(base_tree_list):
        if base_tree.children[0].children[0].child_count == 0:
            continue
        api_name = base_tree.children[0].children[0].children[0].text
        for candidate_tree in candidate_subtree_list:
            if candidate_tree[3] == api_name:
                break
        candidate_tree = candidate_tree[2]
        args_list = get_args(base_tree)
        if len(args_list) == 0:
            continue
        ast_match = all(
            (
                arg.decode().lstrip("'").rstrip("'") in candidate_tree.text.decode()
                for arg in args_list
            )
        )
        if ast_match:
            return idx
    return -1


def ast_eval_tf(api_database, qa_pairs, ast_database, question_id, response):
    output = response
    output = output.split("api_call")
    if len(output) == 1:
        api_call = output[0]
    else:
        output = output[1].split("api_provider")[0]
        start = 0 if ":" not in output else output.index(":")
        end = -2 if ")" not in output else output.rindex(")")
        api_call = output[start + 2 : end + 1]
    ast_tree = ast_parse(api_call)
    ast_subtree_list = get_all_sub_trees(ast_tree)
    database_index = ast_check(ast_subtree_list, ast_database)
    hallucination = database_index == -1
    ref_api_call = api_database[database_index]
    correct = ref_api_call["domain"] == qa_pairs[question_id - 1]["domain"]
    return (correct, hallucination)
