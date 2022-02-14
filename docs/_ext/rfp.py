from typing import List, Any, Dict, cast
from collections import defaultdict

from docutils import nodes
from docutils.parsers.rst import directives

from sphinx import addnodes
from sphinx.directives import ObjectDescription, SphinxDirective
from sphinx.domains import Domain, Index
from sphinx.roles import XRefRole
from sphinx.util.nodes import make_refnode


class rfpreq(nodes.section, nodes.Element):
    pass


def visit_rfpreq_node(self, node):
    self.visit_section(node)


def depart_rfpreq_node(self, node):
    self.depart_section(node)


class RFPReqDirective(SphinxDirective):
    """A custom directive that describes an RFP requirement."""

    has_content = True
    option_spec = {
        'id': directives.unchanged_required,
    }

    def run(self):
        if 'id' not in self.options:
            raise RuntimeError("Missing description or id: %s" % self.options)

        id = self.options['id']

        targetid = 'rfp-req-%s' % id
        targetnode = nodes.target('', '', ids=[targetid])

        rfpreq_node = rfpreq()
        rfpreq_node += nodes.title(f'RFP requirement #{id}', f'Requirement {id}')
        self.state.nested_parse(self.content, self.content_offset, rfpreq_node)

        rfp_reqs = cast(RFPDomain, self.env.get_domain('rfp'))
        rfp_reqs.add_rfp_req(id)
 
        return [targetnode, rfpreq_node]


class RFPDomain(Domain):

    name = 'rfp'
    label = 'RFP requirement'
    roles = {
        'req': XRefRole()
    }
    directives = {
        'req': RFPReqDirective,
    }
    initial_data: Dict[str, List[Any]] = {
        'rfp_reqs': [],  # object list
    }

    def get_full_qualified_name(self, node):
        return '{}.{}'.format('rfp-req', node.arguments[0])

    def get_objects(self):
        for obj in self.data['rfp_reqs']:
            yield(obj)

    def resolve_xref(self, env, fromdocname, builder, typ, target, node,
                     contnode):
        match = [(docname, anchor, name, sig)
                 for name, sig, typ, docname, anchor, prio
                 in self.get_objects() if name == f'rfp-req.{target}']

        if len(match) > 0:
            todocname, targ, name, sig = match[0]
            contnode = nodes.inline(text=f'RFP requirement {target}')
            return make_refnode(builder, fromdocname, todocname, targ,
                                contnode, targ)
        else:
            return None

    def add_rfp_req(self, signature):
        """Add a new RFP requirement to the domain."""

        name = '{}.{}'.format('rfp-req', signature)
        anchor = 'rfp-req-{}'.format(signature)

        self.data['rfp_reqs'].append(
            (name, signature, 'RFP requirement', self.env.docname, anchor, 0))


def setup(app):
    app.add_domain(RFPDomain)
    app.add_node(rfpreq,
                 html=(visit_rfpreq_node, depart_rfpreq_node),
                 latex=(visit_rfpreq_node, depart_rfpreq_node),
                 text=(visit_rfpreq_node, depart_rfpreq_node))

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
