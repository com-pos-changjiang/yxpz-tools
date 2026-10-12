"""命令行入口。"""

import argparse
import sys

from .core import greet, random_string, slugify


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="yxpz", description="yxpz-tools 命令行工具")
    sub = parser.add_subparsers(dest="command")

    p_greet = sub.add_parser("greet", help="打个招呼")
    p_greet.add_argument("name", nargs="?", default="World", help="要问候的名字")

    p_slug = sub.add_parser("slug", help="转换成 slug")
    p_slug.add_argument("text", help="原始文本")

    p_rand = sub.add_parser("rand", help="生成随机字符串")
    p_rand.add_argument("length", nargs="?", type=int, default=8, help="长度，默认 8")

    args = parser.parse_args(argv)

    if args.command == "greet":
        print(greet(args.name))
    elif args.command == "slug":
        print(slugify(args.text))
    elif args.command == "rand":
        print(random_string(args.length))
    else:
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
