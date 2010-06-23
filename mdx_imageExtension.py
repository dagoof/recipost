import markdown, os

IMAGE_LINK_RE = r'\!\s*\((<.*?>|([^\)]*))\)'

class ImagePattern(markdown.inlinepatterns.LinkPattern):
    def handleMatch(self, m):
        el=markdown.etree.Element('img')
        src_parts=m.group(2).split()
        if src_parts:
            src=src_parts[0]
            if src[0] == '<' and src[-1]== '>':
                src=src[1:-1]
            el.set('src', os.path.join('/static/img', self.sanitize_url(src)))
        else:
            el.set('src', '')
        if len(src_parts)>1:
            el.set('title', dequote(' '.join(src_parts[1:])))
        return el
        
class ImagePatternExtension(markdown.Extension):
    def extendMarkdown(self, md, md_globals):
        self.safeMode=True
        md.inlinePatterns.add('extra_image_link', ImagePattern(IMAGE_LINK_RE, self), '<automail')
        #md.inlinePatterns['image_link']=ImagePattern(IMAGE_LINK_RE, self)

def makeExtension(configs=None):
    return ImagePatternExtension(configs=configs)
