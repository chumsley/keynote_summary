import sys
import hashlib
from keynote_parser.file_utils import file_reader
from keynote_parser.codec import IWAFile

#TODO
# - hash the slides to detect unprinted changes

class KeynoteFile(object):
    def __init__(self, fname):
        self.fname = fname
        self._slides = dict()
        self.process()

    #TEST
    def path_archives(self, path):
        for fname, handle in file_reader(self.fname, False):
            if fname == path:
                f = IWAFile.from_buffer(handle.read())
                return f.chunks[0].to_dict()['archives']
        raise KeyError("No such path: '%s'" % path)

    @property
    def slides(self):
        return [self._slides[k] for k in self._slide_order]
             

    def process(self):
        for fname, handle in file_reader(self.fname, False):
            if fname == 'Index/Document.iwa':
                f = IWAFile.from_buffer(handle.read())
                self.process_Document(f.chunks[0].to_dict()['archives'])
            elif fname.startswith('Index/Slide') and fname.endswith('.iwa'):
                f = IWAFile.from_buffer(handle.read())
                self.process_Slide(f.chunks[0].to_dict()['archives'])

    def process_Document(self, archives):
        self._document_archives = archives

        h = {}
        self._slide_flags = {}
        for ar in archives:
            if 'slideTree' in ar['objects'][0]:
                slide_order = [ int(x['identifier']) for x in ar['objects'][0]['slideTree']['slides'] ]
                
            if 'slide' in ar['objects'][0]:
                k = int(ar['header']['identifier'])
                v = int(ar['objects'][0]['slide']['identifier'])
                h[k] = v
                self._slide_flags[v] = {'isHidden': ar['objects'][0]['isHidden'],
                                        'depth': ar['objects'][0]['depth']}

        self._slide_order = [h[k] for k in slide_order]
        for i,v in enumerate(self._slide_order):
            self._slide_flags[v]['slide_number'] = i + 1
            
    def process_Slide(self, archives):
        identifier = int(archives[0]['header']['identifier'])
        self._slides[identifier] = Slide(archives, **self._slide_flags[identifier])

    def hash_slide(self):
        with open(self.fname, 'rb') as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        return "# Presentation hash: %s" % digest

    def markdown(self):
        return "\n\n".join([s.markdown() for s in self.slides] +
                           [self.hash_slide()])

class Slide(object):
    def __init__(self, archives, isHidden=None, depth=None, slide_number=None):
        self._archives = archives
        self.isHidden = isHidden
        self.depth = depth
        self.slide_number = slide_number
        self._objects = []
        self._eqns = []
        self.process()

    def process(self):
        identifier = self._archives[0]['header']['identifier']
        self.identifier = int(identifier)
        num_eqns = 0
        
        for ar in self._archives:
            obj = self.Note.build(ar) or self.Text.build(ar)
            if obj:
                self._objects.append(obj)
                obj._eqns = self._eqns
            else:
                obj = self.Equation.build(ar)
                if obj:
                    self._objects.append(obj)
                    self._eqns.append(obj)
                    num_eqns = num_eqns + 1
                    obj.idx = num_eqns
            # else:
            #     print("!couldn't process %s" % ar['objects'][0]) #TEST
    
    def title(self):
        return str(self._objects[0]).replace("\n\n", " ")
    
    def markdown(self):
        depth = self.depth or 1
        slidenum = " %d: " % self.slide_number if self.slide_number else " "

        eqns = self._eqns.copy()
        objs = self._objects.copy()
        
        def cook(obj, eqns=eqns, objs=objs):
            TAG = b'\xef\xbf\xbc'.decode()
            para = str(obj)
            while para.find(TAG) >= 0:
                s = para.find(TAG)
                e = s + len(TAG)
                para = para[0:s] + str(eqns[0]) + para[e:]
                if eqns[0] in objs:
                    objs.remove(eqns[0])
                # else:
                #     print("%s not in objs?" % str(eqns[0])) #TEST
                eqns = eqns[1:]
            return para

        paras = [ "#" * depth + slidenum + cook(self.title()) ]
        for obj in objs:
            paras.append(cook(obj))

        return "\n\n".join(paras)

    def __repr__(self):
        slidestr = "Slide %d" % self.slide_number if self.slide_number else "Slide"
        titlestr = self.title().replace("\n", " ")
        if len(titlestr) > 35:
            titlestr = titlestr[:32] + "..."            
        return "<%s: '%s'>" % (slidestr, titlestr)
    
    class SlideObject(object):
        text_attr = None

        @classmethod
        def build(cls, archive):
            if cls.text_attr and cls.text_attr in archive['objects'][0]:
                obj = cls(archive)
                if obj.valid:
                    return obj
        
        def __init__(self, archive):
            self._archive = archive
            self._eqns = None
            if self.text_attr:
                self._text = [obj.encode('utf-8') for obj in archive['objects'][0][self.text_attr] if obj != u'\ufffc']

        def __str__(self):
            return ''.join([para.replace(b'\n', b'\n\n').replace(b'\xe2\x80\xa8', b'\n').decode('utf-8') for para in self._text])

        @property
        def valid(self):
            return len(self._text) > 0

    class Text(SlideObject):
        text_attr = 'text'

    class Note(Text):
        def __str__(self):
            return "**NOTES:**\n%s" % super(Slide.Note, self).__str__()

        @property
        def valid(self):
            if super(Slide.Note, self).valid:
                return 'kind' in self._archive['objects'][0] and self._archive['objects'][0]['kind']=='NOTE'
            else:
                return False
        
    class Equation(SlideObject):
        text_attr = '[TSWP.EquationInfoArchive.equation_source_text]'

        def __init__(self, archive):
            super(Slide.Equation, self).__init__(archive)
            self.idx = 0

        def __str__(self):
            return "$%s$" % super(Slide.Equation, self).__str__()

def main():
    fname = sys.argv[1]
    knfile = KeynoteFile(fname)
    print(knfile.markdown())
    
if __name__ == '__main__':
    main()
