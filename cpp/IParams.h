#ifndef IPARAMS_H
#define IPARAMS_H

#include <vector>

namespace eye {

class IParams {
public:
    virtual ~IParams() {}
    virtual std::vector<char> getParams() {
        return std::vector<char> {};
    };
    virtual void setParams(std::vector<char>) {};
};

}

#endif // IPARAMS_H
