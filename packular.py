#!/usr/bin/env python

"""Packular reads lists of required JavaScript and CSS files,
and downloads/combines/references them in index.html files for use in
development and production.
"""

from ConfigParser import ConfigParser
from optparse import OptionParser

from itertools import chain
import os.path as osp
from os import system
import sys


DEFAULT_CONFIG = dict(
        conf_file  = '',

        index_tmpl = 'index-template.html',
        index_dev  = 'index-den.html',
        index_prod = 'index-prod.html',

        outdir_js  = 'lib/',
        outdir_css = 'lib/',

        prod_js   = 'production.js',
        prod_css  = 'production.css',
        prod_tmpl = 'template-cache.js',
        devl_tmpl = '',

        url_js   = [],
        url_css  = [],
        url_tmpl = [],
)

# Templates
SCRIPT = """<script src="%s"></script>"""
LINK = """<link rel="stylesheet" href="%s" />"""
ANGULAR = """angular.module("templatecache", []).run(["$templateCache",
function($templateCache) { %s }]);"""
TMPL = """$templateCache.put("%s", "%s");"""

# Replace this in index_tmpl
AUTOGEN = """<!-- AUTOGENERATED -->"""



def parse_options(default):
    """Parse command line options"""

    opt = OptionParser()
    opt.description = __doc__
    opt.set_defaults(**default)

    opt.add_option('-C', '--config',
            dest = 'conf_file', action = 'store', type = 'string',
            help = "Packular configuration file")

    opt.add_option('--index-template',
            dest = 'index_tmpl', action = 'store', type = 'string',
            help = "Input template file for index.html")
    opt.add_option('--index-dev',
            dest = 'index_dev', action = 'store', type = 'string',
            help = "Output index.html for development")
    opt.add_option('--index-prod',
            dest = 'index_prod', action = 'store', type = 'string',
            help = "Output index.html for production")

    opt.add_option('--outdir_js',
            dest = 'outdir_js', action = 'store', type = 'string',
            help = "Output directory for downloaded JavaScript files")
    opt.add_option('--outdir_css',
            dest = 'outdir_css', action = 'store', type = 'string',
            help = "Output directory for downloaded StyleSheet files")

    opt.add_option('--prod-js',
            dest = 'prod_js', action = 'store', type = 'string',
            help = "Output filename minified JavaScript for production")
    opt.add_option('--prod-css',
            dest = 'prod_css', action = 'store', type = 'string',
            help = "Output filename minified CSS for production")
    opt.add_option('--prod-tmpl',
            dest = 'prod_tmpl', action = 'store', type = 'string',
            help = "Output filename cached templates for production")
    opt.add_option('--dev-tmpl',
            dest = 'devl_tmpl', action = 'store', type = 'string',
            help = "Output filename empty template cache for development")

    opt.add_option('-j', '--javascript',
            dest = 'url_js', action = 'append', type = 'string',
            help = "JavaScript URL, use once for each file. URLs from " +
            "the config file are written first. Prefix filename with ! " +
            "to include in production only, ? to include in development only.")
    opt.add_option('-c', '--css',
            dest = 'url_css', action = 'append', type = 'string',
            help = "StyleSheet URL, use once for each file")
    opt.add_option('-p', '--partial',
            dest = 'url_tmpl', action = 'append', type = 'string',
            help = "Partial HTML URL, use once for each file")

    return opt.parse_args()[0], opt


def read_config(config_file, default):
    """read configuration file"""

    cfg = ConfigParser(allow_no_value=True)
    cfg.read(config_file)

    if cfg.has_section('index'):
        default.update(
                index_tmpl = cfg.get('index', 'template'),
                index_dev  = cfg.get('index', 'dev'),
                index_prod = cfg.get('index', 'prod'),
                )

    if cfg.has_section('output'):
        default.update(
                outdir_js  = cfg.get('output', 'dir_js'),
                outdir_css = cfg.get('output', 'dir_css'),
                prod_js   = cfg.get('output', 'prod_js'),
                prod_css  = cfg.get('output', 'prod_css'),
                prod_tmpl = cfg.get('output', 'prod_tmpl'),
                devl_tmpl = cfg.get('output', 'devl_tmpl'),
                )

    if cfg.has_section('javascript'):
        default.update(url_js = cfg.options('javascript'))

    if cfg.has_section('css'):
        default.update(url_css = cfg.options('css'))

    if cfg.has_section('partial'):
        default.update(url_tmpl = cfg.options('partial'))

    return default


def configure():
    """read configuration from command line options and config file values"""

    opts, parser = parse_options(DEFAULT_CONFIG)

    # re-parse with config file values as defaults
    if opts.conf_file:
        cfg = read_config(opts.conf_file, DEFAULT_CONFIG)
        opts, _ = parse_options(cfg)
    # no config and no command line options
    elif len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    return opts



def combine_nonlocal(urls, fname):
    """merge content of all local files into one file `fname`,
    return list of non-local urls"""

    combine = []

    for url in urls:
        if url.startswith('?'):
            continue
        elif url.startswith('!'):
            url = url[1:]
        if url.startswith('//'):
            yield url
        else:
            print url
            combine.append(file('.' + url).read())

    with file(fname, 'w') as comb:
        print "->", fname
        comb.write('\n'.join(combine))
    yield '/' + fname


def prod_index(index, opts):
    """generate index.html for production usage"""
    prod_js = combine_nonlocal(opts.url_js, opts.prod_js)
    prod_css = combine_nonlocal(opts.url_css, opts.prod_css)

    prod_src = "\n".join(chain(
            (SCRIPT % script_file for script_file in prod_js),
            (LINK % css_file for css_file in prod_css),
            ))

    with file(opts.index_prod, 'w') as prod:
        prod.write(index.replace(AUTOGEN, prod_src))


def make_local(urls, out_dir):
    """download non-local urls into out_dir, return list of all-local urls"""
    for url in urls:
        if url.startswith('!'):
            continue
        elif url.startswith('?'):
            url = url[1:]
        if url.startswith('//'):
            url = url.replace('.min.', '.')
            fname = osp.join(out_dir, osp.basename(url))
            if system('curl -s -o %s %s' % (fname, 'https:' + url,)) != 0:
                system('curl -s -o %s %s' % (fname, 'http:' + url,))
            print url, "->", fname
            yield '/' + fname
        else:
            yield url


def devl_index(index, opts):
    """generate index.html for development usage"""
    dev_src = "\n".join(chain(
            (SCRIPT % script_file for script_file 
                in make_local(opts.url_js, opts.outdir_js)),
            (LINK % css_file for css_file 
                in make_local(opts.url_css, opts.outdir_css)),
            ))

    with file(opts.index_dev, 'w') as devl:
        devl.write(index.replace(AUTOGEN, dev_src))


def prod_tmpl(opts):
    """Read HTML templates and convert into angular $templateCache call"""
    if not opts.prod_tmpl:
        return

    def html2js(url):
        """convert HTML into JavaScript string"""
        data = file('.' + url).read(). \
                replace('"', r'\"').replace('\n', r'\n')
        # angular would not cache the empty string
        return url, data or "<!-- empty -->"

    tmpls = [TMPL % html2js(url) for url in opts.url_tmpl]

    with file(opts.prod_tmpl, 'w') as tmpl:
        tmpl.write(ANGULAR % ('\n'.join(tmpls),))

def devl_tmpl(opts):
    """Write empty $templateCache"""
    if not opts.devl_tmpl:
        return
    with file(opts.devl_tmpl, 'w') as tmpl:
        tmpl.write(ANGULAR % ('',))



def main():
    """entry point"""
    opts = configure()
    index = file(opts.index_tmpl).read()
    prod_tmpl(opts)
    devl_tmpl(opts)
    prod_index(index, opts)
    devl_index(index, opts)

if __name__ == '__main__':
    main()
