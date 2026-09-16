import datetime
import requests
import os
from lxml import etree
import time
import hashlib

# Fine-grained personal access token needs, at minimum:
# Account permissions:    read:Followers, read:Starring, read:Watching
# Repository permissions: read:Commit statuses, read:Contents, read:Metadata
HEADERS = {'authorization': 'token ' + os.environ['ACCESS_TOKEN']}
USER_NAME = os.environ['USER_NAME']  # e.g. 'samyogsilwal61-svg'
QUERY_COUNT = {'user_getter': 0, 'follower_getter': 0, 'graph_repos_stars': 0, 'recursive_loc': 0, 'graph_commits': 0, 'loc_query': 0}


def simple_request(func_name, query, variables):
    """Returns a request, or raises an Exception if the response does not succeed."""
    request = requests.post('https://api.github.com/graphql', json={'query': query, 'variables': variables}, headers=HEADERS)
    if request.status_code == 200:
        return request
    raise Exception(func_name, ' has failed with a', request.status_code, request.text, QUERY_COUNT)


def graph_commits(start_date, end_date):
    """Uses GitHub's GraphQL v4 API to return total commit/contribution count in a window."""
    query_count('graph_commits')
    query = '''
    query($start_date: DateTime!, $end_date: DateTime!, $login: String!) {
        user(login: $login) {
            contributionsCollection(from: $start_date, to: $end_date) {
                contributionCalendar { totalContributions }
            }
        }
    }'''
    variables = {'start_date': start_date, 'end_date': end_date, 'login': USER_NAME}
    request = simple_request(graph_commits.__name__, query, variables)
    return int(request.json()['data']['user']['contributionsCollection']['contributionCalendar']['totalContributions'])


def graph_repos_stars(count_type, owner_affiliation, cursor=None):
    """Uses GitHub's GraphQL v4 API to return total repository or star count."""
    query_count('graph_repos_stars')
    query = '''
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 100, after: $cursor, ownerAffiliations: $owner_affiliation) {
                totalCount
                edges { node { ... on Repository { nameWithOwner stargazers { totalCount } } } }
                pageInfo { endCursor hasNextPage }
            }
        }
    }'''
    variables = {'owner_affiliation': owner_affiliation, 'login': USER_NAME, 'cursor': cursor}
    request = simple_request(graph_repos_stars.__name__, query, variables)
    if count_type == 'repos':
        return request.json()['data']['user']['repositories']['totalCount']
    elif count_type == 'stars':
        return stars_counter(request.json()['data']['user']['repositories']['edges'])


def recursive_loc(owner, repo_name, data, cache_comment, addition_total=0, deletion_total=0, my_commits=0, cursor=None):
    """Uses GitHub's GraphQL v4 API and cursor pagination to fetch 100 commits at a time."""
    query_count('recursive_loc')
    query = '''
    query ($repo_name: String!, $owner: String!, $cursor: String) {
        repository(name: $repo_name, owner: $owner) {
            defaultBranchRef {
                target {
                    ... on Commit {
                        history(first: 100, after: $cursor) {
                            totalCount
                            edges { node { ... on Commit { committedDate } author { user { id } } deletions additions } }
                            pageInfo { endCursor hasNextPage }
                        }
                    }
                }
            }
        }
    }'''
    variables = {'repo_name': repo_name, 'owner': owner, 'cursor': cursor}
    request = requests.post('https://api.github.com/graphql', json={'query': query, 'variables': variables}, headers=HEADERS)
    if request.status_code == 200:
        if request.json()['data']['repository']['defaultBranchRef'] is not None:
            return loc_counter_one_repo(owner, repo_name, data, cache_comment, request.json()['data']['repository']['defaultBranchRef']['target']['history'], addition_total, deletion_total, my_commits)
        else:
            return 0, 0, 0
    force_close_file(data, cache_comment)
    if request.status_code == 403:
        raise Exception('Too many requests in a short amount of time! You\'ve hit the anti-abuse limit.')
    raise Exception('recursive_loc() has failed with a', request.status_code, request.text, QUERY_COUNT)


def loc_counter_one_repo(owner, repo_name, data, cache_comment, history, addition_total, deletion_total, my_commits):
    """Recursively call recursive_loc; only counts commits authored by me."""
    for node in history['edges']:
        if node['node']['author']['user'] == OWNER_ID:
            my_commits += 1
            addition_total += node['node']['additions']
            deletion_total += node['node']['deletions']

    if not history['edges'] or not history['pageInfo']['hasNextPage']:
        return addition_total, deletion_total, my_commits
    return recursive_loc(owner, repo_name, data, cache_comment, addition_total, deletion_total, my_commits, history['pageInfo']['endCursor'])


def loc_query(owner_affiliation, comment_size=0, force_cache=False, cursor=None, edges=None):
    """Queries every repo the user has access to and returns total LOC added/deleted."""
    if edges is None:
        edges = []
    query_count('loc_query')
    query = '''
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 60, after: $cursor, ownerAffiliations: $owner_affiliation) {
                edges { node { ... on Repository { nameWithOwner defaultBranchRef { target { ... on Commit { history { totalCount } } } } } } }
                pageInfo { endCursor hasNextPage }
            }
        }
    }'''
    variables = {'owner_affiliation': owner_affiliation, 'login': USER_NAME, 'cursor': cursor}
    request = simple_request(loc_query.__name__, query, variables)
    new_edges = request.json()['data']['user']['repositories']['edges']
    # Drop any repo GitHub returned a null node for -- the token can't fully
    # see it (commonly: an org-owned repo the token isn't approved for).
    # Better to undercount that one repo than crash the whole run.
    new_edges = [e for e in new_edges if e.get('node')]
    if request.json()['data']['user']['repositories']['pageInfo']['hasNextPage']:
        edges += new_edges
        return loc_query(owner_affiliation, comment_size, force_cache, request.json()['data']['user']['repositories']['pageInfo']['endCursor'], edges)
    else:
        return cache_builder(edges + new_edges, comment_size, force_cache)


def cache_builder(edges, comment_size, force_cache, loc_add=0, loc_del=0):
    """Only re-walks a repo's commits if its commit count changed since the last cached run."""
    cached = True
    filename = 'cache/' + hashlib.sha256(USER_NAME.encode('utf-8')).hexdigest() + '.txt'
    try:
        with open(filename, 'r') as f:
            data = f.readlines()
    except FileNotFoundError:
        data = []
        if comment_size > 0:
            for _ in range(comment_size):
                data.append('This line is a comment block. Write whatever you want here.\n')
        os.makedirs('cache', exist_ok=True)
        with open(filename, 'w') as f:
            f.writelines(data)

    if len(data) - comment_size != len(edges) or force_cache:
        cached = False
        flush_cache(edges, filename, comment_size)
        with open(filename, 'r') as f:
            data = f.readlines()

    cache_comment = data[:comment_size]
    data = data[comment_size:]
    for index in range(len(edges)):
        repo_hash, commit_count, *__ = data[index].split()
        if repo_hash == hashlib.sha256(edges[index]['node']['nameWithOwner'].encode('utf-8')).hexdigest():
            try:
                if int(commit_count) != edges[index]['node']['defaultBranchRef']['target']['history']['totalCount']:
                    owner, repo_name = edges[index]['node']['nameWithOwner'].split('/')
                    loc = recursive_loc(owner, repo_name, data, cache_comment)
                    data[index] = repo_hash + ' ' + str(edges[index]['node']['defaultBranchRef']['target']['history']['totalCount']) + ' ' + str(loc[2]) + ' ' + str(loc[0]) + ' ' + str(loc[1]) + '\n'
            except TypeError:
                data[index] = repo_hash + ' 0 0 0 0\n'
    with open(filename, 'w') as f:
        f.writelines(cache_comment)
        f.writelines(data)

    for line in data:
        loc = line.split()
        loc_add += int(loc[3])
        loc_del += int(loc[4])
    return [loc_add, loc_del, loc_add - loc_del, cached]


def flush_cache(edges, filename, comment_size):
    """Wipes and rebuilds the cache file when the repo count changes."""
    with open(filename, 'r') as f:
        data = f.readlines()[:comment_size] if comment_size > 0 else []
    with open(filename, 'w') as f:
        f.writelines(data)
        for node in edges:
            f.write(hashlib.sha256(node['node']['nameWithOwner'].encode('utf-8')).hexdigest() + ' 0 0 0 0\n')


def force_close_file(data, cache_comment):
    """Preserves partial cache data if the script crashes mid-run."""
    filename = 'cache/' + hashlib.sha256(USER_NAME.encode('utf-8')).hexdigest() + '.txt'
    with open(filename, 'w') as f:
        f.writelines(cache_comment)
        f.writelines(data)
    print('There was an error while writing to the cache file. Partial data was saved to', filename)


def stars_counter(data):
    total_stars = 0
    for node in data:
        repo = node.get('node')
        if not repo:
            # GitHub returns a null node for a repo the token can't fully see
            # (commonly: an org-owned repo the token isn't approved for).
            # Skip it rather than crash the whole run.
            continue
        total_stars += repo['stargazers']['totalCount']
    return total_stars


def svg_overwrite(filename, commit_data, star_data, repo_data, contrib_data, follower_data, loc_data):
    """Parses the SVG and updates every element whose id matches a stat."""
    tree = etree.parse(filename)
    root = tree.getroot()
    justify_format(root, 'commit_data', commit_data, 5)
    justify_format(root, 'star_data', star_data, 8)
    justify_format(root, 'repo_data', repo_data, 5)
    justify_format(root, 'contrib_data', contrib_data)
    justify_format(root, 'follower_data', follower_data, 8)
    justify_format(root, 'loc_data', loc_data[2])
    justify_format(root, 'loc_add', loc_data[0])
    justify_format(root, 'loc_del', loc_data[1])
    tree.write(filename, encoding='utf-8', xml_declaration=True)


def justify_format(root, element_id, new_text, length=0):
    """Updates the text of an element and pads the matching *_dots element to keep alignment."""
    if element_id in ('loc_add', 'loc_del'):
        suffix = '++' if element_id == 'loc_add' else '--'
        find_and_replace(root, element_id, f"{'{:,}'.format(new_text)}{suffix}")
        return
    if isinstance(new_text, int):
        new_text = f"{'{:,}'.format(new_text)}"
    new_text = str(new_text)
    find_and_replace(root, element_id, new_text)
    just_len = max(0, length - len(new_text))
    dot_string = '.' * just_len if just_len > 0 else ''
    find_and_replace(root, f"{element_id}_dots", dot_string)


def find_and_replace(root, element_id, new_text):
    element = root.find(f".//*[@id='{element_id}']")
    if element is not None:
        element.text = new_text


def commit_counter(comment_size):
    """Sums total commits from the cache file built by cache_builder."""
    total_commits = 0
    filename = 'cache/' + hashlib.sha256(USER_NAME.encode('utf-8')).hexdigest() + '.txt'
    with open(filename, 'r') as f:
        data = f.readlines()
    data = data[comment_size:]
    for line in data:
        total_commits += int(line.split()[2])
    return total_commits


def user_getter(username):
    query_count('user_getter')
    query = '''
    query($login: String!){ user(login: $login) { id createdAt } }'''
    variables = {'login': username}
    request = simple_request(user_getter.__name__, query, variables)
    return {'id': request.json()['data']['user']['id']}, request.json()['data']['user']['createdAt']


def follower_getter(username):
    query_count('follower_getter')
    query = '''
    query($login: String!){ user(login: $login) { followers { totalCount } } }'''
    request = simple_request(follower_getter.__name__, query, {'login': username})
    return int(request.json()['data']['user']['followers']['totalCount'])


def query_count(funct_id):
    global QUERY_COUNT
    QUERY_COUNT[funct_id] += 1


def perf_counter(funct, *args):
    start = time.perf_counter()
    funct_return = funct(*args)
    return funct_return, time.perf_counter() - start


def formatter(query_type, difference, funct_return=False, whitespace=0):
    print('{:<23}'.format('   ' + query_type + ':'), sep='', end='')
    print('{:>12}'.format('%.4f' % difference + ' s ')) if difference > 1 else print('{:>12}'.format('%.4f' % (difference * 1000) + ' ms'))
    if whitespace:
        return f"{'{:,}'.format(funct_return): <{whitespace}}"
    return funct_return


if __name__ == '__main__':
    print('Calculation times:')
    user_data, user_time = perf_counter(user_getter, USER_NAME)
    OWNER_ID, acc_date = user_data
    formatter('account data', user_time)

    total_loc, loc_time = perf_counter(loc_query, ['OWNER', 'COLLABORATOR', 'ORGANIZATION_MEMBER'], 0)
    formatter('LOC (cached)', loc_time) if total_loc[-1] else formatter('LOC (no cache)', loc_time)

    commit_data, commit_time = perf_counter(commit_counter, 0)
    star_data, star_time = perf_counter(graph_repos_stars, 'stars', ['OWNER'])
    repo_data, repo_time = perf_counter(graph_repos_stars, 'repos', ['OWNER'])
    contrib_data, contrib_time = perf_counter(graph_repos_stars, 'repos', ['OWNER', 'COLLABORATOR', 'ORGANIZATION_MEMBER'])
    follower_data, follower_time = perf_counter(follower_getter, USER_NAME)

    svg_overwrite('dark_mode.svg', commit_data, star_data, repo_data, contrib_data, follower_data, total_loc[:-1])
    svg_overwrite('light_mode.svg', commit_data, star_data, repo_data, contrib_data, follower_data, total_loc[:-1])

    print('\033[F\033[F\033[F\033[F\033[F\033[F\033[F',
          '{:<21}'.format('Total function time:'), '{:>11}'.format('%.4f' % (user_time + loc_time + commit_time + star_time + repo_time + contrib_time)),
          ' s \033[E\033[E\033[E\033[E\033[E\033[E\033[E', sep='')
    print('Total GitHub GraphQL API calls:', '{:>3}'.format(sum(QUERY_COUNT.values())))
    for funct_name, count in QUERY_COUNT.items():
        print('{:<28}'.format('   ' + funct_name + ':'), '{:>6}'.format(count))
